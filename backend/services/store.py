import datetime

from models import Artist, Album, Track, AlbumArtist, TrackArtist, Playlist
from sqlmodel import Session


ALLOWED_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m",
)


def parse_date(date_str):
    if isinstance(date_str, str):
        if len(date_str) == 4:
            date_str += "-01-01"  # %Y, let's add Jan01
        elif len(date_str) == 7:
            date_str += "-01"  # %Y-%M, let's add the day to be able to parse
        date_str = date_str.strip()
        for date_fmt in ALLOWED_DATETIME_FORMATS:
            try:
                return datetime.datetime.strptime(date_str, date_fmt)
            except ValueError:
                pass
        raise ValueError(
            f"Invalid date: '{date_str}', please pass a datetime or a string format"
        )
    return date_str


def store_track(track, db_session: Session):
    """Store a track and its related data using SQLModel merge for efficient upserts"""
    artists = []
    for artist_data in track.get("artists", []):
        # Create artist instance and merge (upsert)
        artist = Artist(
            id=artist_data["id"],
            name=artist_data["name"],
            picture=artist_data.get("picture"),
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
    )
    t = db_session.merge(t)

    # Handle track artists relationships
    for artist in artists:
        track_artist_relation = TrackArtist(track_id=t.id, artist_id=artist.id)
        db_session.merge(track_artist_relation)

    # Commit all changes
    db_session.commit()
    return t


def store_playlist(playlist: dict, db_session: Session):
    p = Playlist(
        id=playlist["id"],
        name=playlist["name"],
        description=playlist["description"],
        picture=playlist["images"][0]["url"] if playlist.get("images") else None,
        owner_id=playlist["owner"]["id"],
        is_public=playlist["public"],
    )
    p = db_session.merge(p)
    db_session.commit()
    return p
