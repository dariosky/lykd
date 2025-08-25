from sqlmodel import Session, delete, select, update, func

from models.auth import User
from models.music import (
    Artist,
    Album,
    AlbumArtist,
    Track,
    TrackArtist,
    Playlist,
    Like,
    PlaylistTrack,
    Play,
)
import logging

from utils.dates import parse_date
from sqlalchemy import text

logger = logging.getLogger("lykd.store")


def store_track(track, db_session: Session):
    """Store a track and its related data using SQLModel merge for efficient upserts"""
    artists = []
    for artist_data in track.get("artists", []):
        if not artist_data.get("id") or not artist_data.get("name"):
            logger.error(f"Invalid artist data, skipping: {artist_data}")
            continue
        # Create artist instance and merge (upsert)
        try:
            artist = Artist(
                id=artist_data["id"],
                name=artist_data["name"],
                picture=artist_data.get("picture"),
                uri=artist_data.get("uri"),
            )
            merged_artist = db_session.merge(artist)
            artists.append(merged_artist)
        except Exception as e:
            logger.error(f"Error storing Artist: {e} - {artist_data}")

    album = None
    if track.get("album"):
        album_data = track["album"]

        # Create album instance and merge (upsert)
        try:
            try:
                release_date = (
                    parse_date(album_data["release_date"]).date()
                    if album_data.get("release_date")
                    else None
                )
            except Exception:
                logger.error(
                    f"Error parsing album release date: {album_data['release_date']}"
                )
                release_date = None
            album = Album(
                id=album_data["id"],
                name=album_data["name"],
                release_date=release_date,
                release_date_precision=album_data.get("release_date_precision"),
                picture=album_data["images"][0]["url"]
                if album_data.get("images")
                else None,
                uri=album_data.get("uri"),
            )
            album = db_session.merge(album)
        except Exception as e:
            logger.error(f"Error storing album: {e} - {album_data}")

        # Handle album artists
        for artist_data in album_data.get("artists", []):
            if not artist_data.get("id") or not artist_data.get("name"):
                logger.error(f"Invalid album artist data, skipping: {artist_data}")
                continue
            try:
                # Create/merge album artist
                album_artist = Artist(
                    id=artist_data["id"],
                    name=artist_data["name"],
                    picture=artist_data.get("picture"),
                )
                merged_album_artist = db_session.merge(album_artist)

                # Create/merge album-artist relationship
                album_artist_relation = AlbumArtist(
                    album_id=album.id, artist_id=merged_album_artist.id
                )
                db_session.merge(album_artist_relation)
            except Exception as e:
                logger.error(f"Error storing album artist: {e} - {artist_data}")

    # Create track instance and merge (upsert)
    t = Track(
        id=track["id"],
        title=track["name"],
        duration=track["duration_ms"],
        album_id=album.id if album else None,
        uri=track["uri"],
    )
    t = db_session.merge(t)

    # Handle track artists relationships
    for artist in artists:
        track_artist_relation = TrackArtist(track_id=t.id, artist_id=artist.id)
        db_session.merge(track_artist_relation)

    return t


def store_playlist(playlist: dict, db_session: Session):
    values = dict(
        name=playlist["name"],
        description=playlist["description"],
        picture=playlist["images"][0]["url"] if playlist.get("images") else None,
        owner_id=playlist["owner"]["id"],
        is_public=playlist["public"],
        is_collaborative=playlist["collaborative"],
        uri=playlist["uri"],
    )
    p = db_session.get(Playlist, playlist["id"])
    if p:
        for k, v in values.items():
            setattr(p, k, v)
    else:
        p = Playlist(id=playlist["id"], **values)
        db_session.add(p)
    return p


def update_playlist_db(
    playlist_id: str,
    tracks_to_add: list[PlaylistTrack],
    tracks_to_remove: set[str],
    db: Session,
    snapshot_id: str | None = None,
):
    if tracks_to_remove:
        db.exec(
            delete(PlaylistTrack).where(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.track_id.in_(tuple(tracks_to_remove)),
            )
        )
    for playlist_track in tracks_to_add:
        db.merge(playlist_track)
    if snapshot_id is not None:
        db.exec(
            update(Playlist)
            .where(Playlist.id == playlist_id)
            .values(snapshot_id=snapshot_id)
        )


def update_likes_db(
    user: User, likes_to_add: list[Like], tracks_to_remove: set[str], db: Session
):
    if tracks_to_remove:
        db.exec(
            delete(Like).where(
                Like.user_id == user.id,
                Like.track_id.in_(tuple(tracks_to_remove)),
            )
        )
    for like in likes_to_add:
        db.merge(like)


def find_missing_tracks(session: Session):
    """Find track IDs that appear in plays but have no corresponding track title"""
    query = (
        select(Play.track_id)
        .select_from(Play)
        .join(Track, Play.track_id == Track.id, isouter=True)
        .where(Track.title.is_(None))
    )
    missing_ids = set(session.exec(query).all())
    return missing_ids


def remove_duplicates(db: Session):
    """Remove duplicate likes keeping the oldest per (user_id, track_id).

    Returns a list of tuples (user_id, track_id, count, oldest_date) describing
    the duplicate groups that were found prior to deletion.
    """
    dup_query = (
        select(
            Like.user_id,
            Like.track_id,
            func.count().label("count"),
            func.min(Like.date).label("oldest_date"),
        )
        .group_by(Like.user_id, Like.track_id)
        .having(func.count() > 1)
    )
    duplicates = db.exec(dup_query).all()
    logger.info(f"Removing {len(duplicates)} duplicate tracks")

    # Use a deterministic window function to delete all but one row per group.
    # This handles ties on date by using a stable secondary tiebreaker.
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        db.exec(
            text(
                """
                WITH ranked AS (
                    SELECT rowid AS rid,
                           user_id,
                           track_id,
                           date,
                           ROW_NUMBER() OVER (
                               PARTITION BY user_id, track_id
                               ORDER BY date ASC, rowid ASC
                           ) AS rn
                    FROM likes
                )
                DELETE FROM likes
                WHERE rowid IN (
                    SELECT rid FROM ranked WHERE rn > 1
                );
                """
            )
        )
    elif dialect in ("postgresql", "postgres"):
        db.exec(
            text(
                """
                WITH ranked AS (
                    SELECT ctid,
                           user_id,
                           track_id,
                           date,
                           ROW_NUMBER() OVER (
                               PARTITION BY user_id, track_id
                               ORDER BY date ASC, ctid ASC
                           ) AS rn
                    FROM likes
                )
                DELETE FROM likes l
                USING ranked r
                WHERE l.ctid = r.ctid AND r.rn > 1;
                """
            )
        )
    else:
        # Generic fallback: remove rows strictly newer than the min(date) as before.
        # This may leave duplicates if dates are exactly equal on unsupported dialects.
        for user_id, track_id, _count, oldest_date in duplicates:
            db.exec(
                delete(Like).where(
                    Like.user_id == user_id,
                    Like.track_id == track_id,
                    Like.date > oldest_date,
                )
            )

    db.commit()
    return duplicates
