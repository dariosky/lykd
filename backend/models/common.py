"""Common database utilities and base models"""

import datetime
from contextlib import contextmanager

import sqlmodel
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlmodel import create_engine, Session, Field
from typing import Generator

import logging

logger = logging.getLogger("lykd.db")


def get_engine():  # pragma: no cover
    from settings import DATABASE_URL

    return create_engine(DATABASE_URL)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoggedModel(sqlmodel.SQLModel, CamelModel):
    updated_at: datetime.datetime = Field(default=None, nullable=True)
    updated_by: str = Field(default=None, nullable=True)


def get_session() -> Generator[Session, None, None]:  # pragma: no cover
    """Get database session for FastAPI dependency, always closes session."""
    session = Session(get_engine(), expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_db() -> Generator[Session, None, None]:  # pragma: no cover
    """Context manager for database session"""
    engine = get_engine()
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
    except Exception as e:
        logger.exception(f"Exception in the database session rolling back - {e}")
        session.rollback()
    finally:
        session.close()
        engine.dispose()


def parse_bool(bool_str: str | bool):
    if isinstance(bool_str, str):
        return bool_str.lower() in ("true", "1")
    return bool(bool_str)
