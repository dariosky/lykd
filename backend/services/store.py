from sqlmodel import Session, Column, delete

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
)
import logging

from utils.dates import parse_date

logger = logging.getLogger("lykd.store")


def store_track(track, db_session: Session):
    """Store a track and its related data using SQLModel merge for efficient upserts"""
    artists = []
    for artist_data in track.get("artists", []):
        # Create artist instance and merge (upsert)
        artist = Artist(
            id=artist_data["id"],
            name=artist_data["name"],
            picture=artist_data.get("picture"),
            uri=artist_data.get("uri"),
        )
        merged_artist = db_session.merge(artist)
        artists.append(merged_artist)

    album = None
    if track.get("album"):
        album_data = track["album"]

        # Create album instance and merge (upsert)
        album = Album(
            id=album_data["id"],
            name=album_data["name"],
            release_date=parse_date(album_data["release_date"]).date()
            if album_data.get("release_date")
            else None,
            release_date_precision=album_data.get("release_date_precision"),
            picture=album_data["images"][0]["url"]
            if album_data.get("images")
            else None,
            uri=album_data.get("uri"),
        )
        album = db_session.merge(album)

        # Handle album artists
        for artist_data in album_data.get("artists", []):
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
    p = Playlist(
        id=playlist["id"],
        name=playlist["name"],
        description=playlist["description"],
        picture=playlist["images"][0]["url"] if playlist.get("images") else None,
        owner_id=playlist["owner"]["id"],
        is_public=playlist["public"],
        uri=playlist["uri"],
    )
    p = db_session.merge(p)
    return p


def update_playlist_db(
    playlist_id: str,
    tracks_to_add: list[PlaylistTrack],
    tracks_to_remove: set[str],
    db: Session,
):
    for playlist_track in tracks_to_add:
        db.merge(playlist_track)
    if tracks_to_remove:
        db.exec(
            delete(PlaylistTrack).where(
                playlist_id == playlist_id,
                Column(Like.track_id).in_(list(tracks_to_remove)),
            )
        )


def update_likes_db(
    user: User, likes_to_add: list[Like], tracks_to_remove: set[str], db: Session
):
    for like in likes_to_add:
        db.merge(like)
    if tracks_to_remove:
        db.exec(
            delete(Like).where(
                Like.user_id == user.id,
                Column(Like.track_id).in_(list(tracks_to_remove)),
            )
        )
