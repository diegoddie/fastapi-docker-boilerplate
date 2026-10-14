"""The commons package types."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import ENUM
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


def pg_enum(enum: type[StrEnum]) -> ENUM:
    """
    Return a Postgres enum type that stores the values of a ``StrEnum``.

    Why: by default SQLAlchemy stores the member names ("IN_PROGRESS"), so the
    database would hold values different from the ones the API and the code use.
    """
    return ENUM(
        enum,
        name=enum.__name__.lower(),
        values_callable=lambda members: [member.value for member in members],
    )
