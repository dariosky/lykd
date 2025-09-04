import datetime
from datetime import timezone
from enum import Enum

from models.common import CamelModel
from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel

from .ignored import (  # noqa
    GlobalIgnoredArtist,
    GlobalIgnoredTrack,
    IgnoredArtist,
    IgnoredTrack,
)


class Artist(SQLModel, CamelModel, table=True):
    __tablename__ = "artists"

    id: str = Field(primary_key=True)
    name: str
    picture: str | None
    uri: str | None = None


class DatePrecision(str, Enum):
    day = "day"
    month = "month"
    year = "year"


class Album(SQLModel, CamelModel, table=True):
    __tablename__ = "albums"

    id: str = Field(primary_key=True)
    name: str
    picture: str | None
    release_date: datetime.date | None
    release_date_precision: DatePrecision | None
    uri: str | None = None


class TrackArtist(SQLModel, CamelModel, table=True):
    __tablename__ = "artists_tracks"

    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    artist_id: str = Field(primary_key=True, foreign_key="artists.id")

    __table_args__ = (
        Index("idx_artists_tracks_track", "track_id"),
        Index("idx_artists_tracks_artist", "artist_id"),
    )


class Track(SQLModel, CamelModel, table=True):
    __tablename__ = "tracks"

    id: str = Field(primary_key=True)
    title: str
    duration: int
    album_id: str | None = Field(default=None, foreign_key="albums.id")

    # Relationship to playlists through PlaylistTrack
    playlist_tracks: list["PlaylistTrack"] = Relationship(back_populates="track")
    uid: str | None = Field(default=None, index=True)

    __table_args__ = (Index("idx_tracks_album_id", "album_id"),)


class AlbumArtist(SQLModel, CamelModel, table=True):
    __tablename__ = "albums_artists"

    album_id: str = Field(primary_key=True, foreign_key="albums.id")
    artist_id: str = Field(primary_key=True, foreign_key="artists.id")


class Play(SQLModel, CamelModel, table=True):
    __tablename__ = "plays"

    user_id: str = Field(primary_key=True, foreign_key="users.id")
    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc), primary_key=True
    )
    context_uri: str | None = Field(default=None)

    __table_args__ = (
        Index("idx_plays_date", "date"),
        Index("idx_plays_user_date", "user_id", "date"),
        Index("idx_plays_user_date_track", "user_id", "date", "track_id"),
        Index("idx_plays_user_track", "user_id", "track_id"),
        Index("idx_plays_track", "track_id"),
    )


class Like(SQLModel, CamelModel, table=True):
    __tablename__ = "likes"

    user_id: str = Field(primary_key=True, foreign_key="users.id")
    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    uid: str | None = Field(primary_key=True, foreign_key="tracks.id", default=None)
    date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )


class PlaylistTrack(SQLModel, CamelModel, table=True):
    __tablename__ = "playlists_tracks"

    playlist_id: str = Field(primary_key=True, foreign_key="playlists.id")
    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )

    # Relationships
    playlist: "Playlist" = Relationship(back_populates="playlist_tracks")
    track: "Track" = Relationship(back_populates="playlist_tracks")


class Playlist(SQLModel, CamelModel, table=True):
    __tablename__ = "playlists"

    id: str = Field(primary_key=True)
    name: str
    description: str | None = None
    picture: str | None = None
    owner_id: str = Field(foreign_key="users.id")
    is_public: bool = True
    is_collaborative: bool = False
    uri: str | None = None
    snapshot_id: str | None = None  # snapshot change when playlist is updated

    # Relationship to get tracks through PlaylistTrack
    playlist_tracks: list["PlaylistTrack"] = Relationship(back_populates="playlist")

    @property
    def tracks(self) -> list["Track"]:
        """Get all tracks in this playlist"""
        return [pt.track for pt in self.playlist_tracks]
