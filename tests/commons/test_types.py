"""The commons types tests."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.engine.interfaces import Dialect

from app.commons.types import UTCDateTime


def test_utc_datetime_bind_param(postgresql_dialect: Dialect) -> None:
    """Test aware datetimes are normalized to UTC before writing."""
    rome = timezone(timedelta(hours=2))
    value = datetime(2026, 1, 1, 12, 0, tzinfo=rome)
    result = UTCDateTime().process_bind_param(value, postgresql_dialect)
    assert result == datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    assert result is not None
    assert result.tzinfo == UTC


def test_utc_datetime_bind_param_none(postgresql_dialect: Dialect) -> None:
    """Test null values are written as they are."""
    assert UTCDateTime().process_bind_param(None, postgresql_dialect) is None


def test_utc_datetime_bind_param_naive(postgresql_dialect: Dialect) -> None:
    """Test naive datetimes are rejected."""
    with pytest.raises(ValueError, match="naive datetime rejected"):
        UTCDateTime().process_bind_param(datetime(2026, 1, 1), postgresql_dialect)


def test_utc_datetime_result_value(postgresql_dialect: Dialect) -> None:
    """Test stored values are returned as aware UTC datetimes."""
    rome = timezone(timedelta(hours=2))
    value = datetime(2026, 1, 1, 12, 0, tzinfo=rome)
    result = UTCDateTime().process_result_value(value, postgresql_dialect)
    assert result is not None
    assert result.tzinfo == UTC
    assert UTCDateTime().process_result_value(None, postgresql_dialect) is None
