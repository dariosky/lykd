import datetime
from datetime import timezone
from enum import Enum

from models.common import CamelModel
from models.types import UtcAwareDateTime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Index, Column, func


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
    uri: str | None = None

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
    date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc), primary_key=True
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
    uri: str | None = None

    # Relationship to get tracks through PlaylistTrack
    playlist_tracks: list["PlaylistTrack"] = Relationship(back_populates="playlist")

    @property
    def tracks(self) -> list["Track"]:
        """Get all tracks in this playlist"""
        return [pt.track for pt in self.playlist_tracks]


class IgnoredTrack(SQLModel, CamelModel, table=True):
    __tablename__ = "ignored_tracks"

    user_id: str = Field(primary_key=True, foreign_key="users.id")
    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    ts: datetime.datetime | None = Field(
        default=datetime.datetime.now(timezone.utc),
        sa_column=Column(UtcAwareDateTime(), onupdate=func.now(), nullable=True),
    )
    reported: bool = Field(default=False)


class IgnoredArtist(SQLModel, CamelModel, table=True):
    __tablename__ = "ignored_artists"

    user_id: str = Field(primary_key=True, foreign_key="users.id")
    artist_id: str = Field(primary_key=True, foreign_key="artists.id")
    ts: datetime.datetime | None = Field(
        default=datetime.datetime.now(timezone.utc),
        sa_column=Column(UtcAwareDateTime(), onupdate=func.now(), nullable=True),
    )
    reported: bool = Field(default=False)


class GlobalIgnoredTrack(SQLModel, CamelModel, table=True):
    __tablename__ = "global_ignored_tracks"

    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    approved_by: str | None = Field(default=None, foreign_key="users.id")
    ts: datetime.datetime | None = Field(
        default=datetime.datetime.now(timezone.utc),
        sa_column=Column(UtcAwareDateTime(), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (Index("idx_global_ignored_tracks_track", "track_id"),)


class GlobalIgnoredArtist(SQLModel, CamelModel, table=True):
    __tablename__ = "global_ignored_artists"

    artist_id: str = Field(primary_key=True, foreign_key="artists.id")
    approved_by: str | None = Field(default=None, foreign_key="users.id")
    ts: datetime.datetime | None = Field(
        default=datetime.datetime.now(timezone.utc),
        sa_column=Column(UtcAwareDateTime(), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (Index("idx_global_ignored_artists_artist", "artist_id"),)
