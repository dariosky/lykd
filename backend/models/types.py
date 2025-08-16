import datetime as _dt
from sqlalchemy.types import TypeDecorator, DateTime


class UtcAwareDateTime(TypeDecorator):
    """Always write UTC and always return tz-aware datetimes (UTC)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            # Accept ISO strings too
            return _dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
                _dt.timezone.utc
            )
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return value.astimezone(_dt.timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            # Some SQLite setups may return strings
            return _dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
                _dt.timezone.utc
            )
        if value.tzinfo is None:
            return value.replace(tzinfo=_dt.timezone.utc)
        return value.astimezone(_dt.timezone.utc)
