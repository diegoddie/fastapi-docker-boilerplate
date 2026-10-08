"""The commons types tests."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import postgresql

from app.commons.types import UTCDateTime

DIALECT = postgresql.dialect()  # type: ignore[no-untyped-call]


def test_utc_datetime_bind_param() -> None:
    """Test aware datetimes are normalized to UTC before writing."""
    rome = timezone(timedelta(hours=2))
    value = datetime(2026, 1, 1, 12, 0, tzinfo=rome)
    result = UTCDateTime().process_bind_param(value, DIALECT)
    assert result == datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    assert result is not None
    assert result.tzinfo == UTC


def test_utc_datetime_bind_param_none() -> None:
    """Test null values are written as they are."""
    assert UTCDateTime().process_bind_param(None, DIALECT) is None


def test_utc_datetime_bind_param_naive() -> None:
    """Test naive datetimes are rejected."""
    with pytest.raises(ValueError, match="naive datetime rejected"):
        UTCDateTime().process_bind_param(datetime(2026, 1, 1), DIALECT)


def test_utc_datetime_result_value() -> None:
    """Test stored values are returned as aware UTC datetimes."""
    rome = timezone(timedelta(hours=2))
    value = datetime(2026, 1, 1, 12, 0, tzinfo=rome)
    result = UTCDateTime().process_result_value(value, DIALECT)
    assert result is not None
    assert result.tzinfo == UTC
    assert UTCDateTime().process_result_value(None, DIALECT) is None
