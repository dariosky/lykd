"""Common database utilities and base models"""

import datetime
from contextlib import contextmanager

import sqlmodel
from cachetools.func import ttl_cache
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlmodel import create_engine, Session, Field
from typing import Generator, Callable


# Create engine
def get_engine():  # pragma: no cover
    from settings import DATABASE_URL

    return create_engine(DATABASE_URL)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoggedModel(sqlmodel.SQLModel, CamelModel):
    updated_at: datetime.datetime = Field(default=None, nullable=True)
    updated_by: str = Field(default=None, nullable=True)


def get_session() -> Generator[Session, None, None]:  # pragma: no cover
    """Get database session"""
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session


@contextmanager
def get_db() -> Generator[Session, None, None]:  # pragma: no cover
    """Context manager for database session"""
    engine = get_engine()
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def parse_bool(bool_str: str | bool):
    if isinstance(bool_str, str):
        return bool_str.lower() in ("true", "1")
    return bool(bool_str)


loggers: dict[int, Callable] = {}


def ratelimited_log(delay_or_fn: int | Callable, msg=None):
    if callable(delay_or_fn):
        logger_method = delay_or_fn
        delay = 60
    else:
        delay = delay_or_fn
        logger_method = None

    if delay not in loggers:

        @ttl_cache(ttl=delay)
        def call(logger_method, message):
            logger_method(message)

        # Store the rate-limited logger function in the loggers dictionary
        loggers[delay] = call

    if logger_method is not None:
        # Call the rate-limited logger function if logger_method is provided
        return loggers[delay](logger_method, msg)
    else:
        # Return the rate-limited logger function for later use
        return loggers[delay]
