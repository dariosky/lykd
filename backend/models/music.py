import datetime
from datetime import timezone
from enum import Enum

from models import CamelModel
from sqlmodel import Field, SQLModel


class Artist(SQLModel, CamelModel, table=True):
    __tablename__ = "artist"

    id: str = Field(primary_key=True)
    name: str
    picture: str | None


class DatePrecision(str, Enum):
    day = "day"
    month = "month"
    year = "year"


class Album(SQLModel, CamelModel, table=True):
    __tablename__ = "album"

    id: str = Field(primary_key=True)
    name: str
    picture: str | None
    release_date: datetime.date | None
    release_date_precision: DatePrecision | None


class TrackArtist(SQLModel, CamelModel, table=True):
    __tablename__ = "track_artist"

    track_id: str = Field(primary_key=True, foreign_key="track.id")
    artist_id: str = Field(primary_key=True, foreign_key="artist.id")


class Track(SQLModel, CamelModel, table=True):
    __tablename__ = "track"

    id: str = Field(primary_key=True)
    title: str
    duration: int
    album_id: str | None = Field(default=None, foreign_key="album.id")


class AlbumArtist(SQLModel, CamelModel, table=True):
    __tablename__ = "album_artist"

    album_id: str = Field(primary_key=True, foreign_key="album.id")
    artist_id: str = Field(primary_key=True, foreign_key="artist.id")


class Play(SQLModel, CamelModel, table=True):
    __tablename__ = "play"

    user_id: str = Field(primary_key=True, foreign_key="user.id")
    track_id: str = Field(primary_key=True, foreign_key="track.id")
    date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc), primary_key=True
    )


class Liked(SQLModel, CamelModel, table=True):
    __tablename__ = "liked"

    user_id: str = Field(primary_key=True, foreign_key="user.id")
    track_id: str = Field(primary_key=True, foreign_key="track.id")
    date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc), primary_key=True
    )
