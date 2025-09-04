import datetime
from datetime import timezone

from models.common import CamelModel
from models.types import UtcAwareDateTime
from sqlalchemy import Column, Index, func
from sqlmodel import Field, SQLModel


class IgnoredTrack(SQLModel, CamelModel, table=True):
    __tablename__ = "ignored_tracks"

    user_id: str = Field(primary_key=True, foreign_key="users.id")
    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    uid: str | None = Field(primary_key=True, foreign_key="tracks.uid", default=None)
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
        sa_column=Column(UtcAwareDateTime(), nullable=True),
    )
    reported: bool = Field(default=False)


class GlobalIgnoredTrack(SQLModel, CamelModel, table=True):
    __tablename__ = "global_ignored_tracks"

    track_id: str = Field(primary_key=True, foreign_key="tracks.id")
    uid: str | None = Field(primary_key=True, foreign_key="tracks.uid", default=None)
    approved_by: str | None = Field(default=None, foreign_key="users.id")
    ts: datetime.datetime | None = Field(
        default=datetime.datetime.now(timezone.utc),
        sa_column=Column(UtcAwareDateTime(), nullable=True),
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
