"""The commons package types."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """
    A ``timestamptz`` column that only stores and returns aware UTC datetimes.

    Naive values are rejected instead of silently being interpreted in the server's
    session timezone, and reads are normalized to UTC so callers never depend on it.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        """Reject naive datetimes and normalize aware ones to UTC before writing."""
        if value is None:
            return None
        if value.tzinfo is None:
            msg = "naive datetime rejected: attach a timezone before persisting"
            raise ValueError(msg)
        return value.astimezone(UTC)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        """Return the stored instant as an aware UTC datetime."""
        return value if value is None else value.astimezone(UTC)
