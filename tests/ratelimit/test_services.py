"""The ratelimit package services tests."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from time_machine import TimeMachineFixture

from app.core.exceptions import TooManyRequestsHTTPException
from app.ratelimit.services import PostgresRateLimiter, RateLimit, get_window


def test_get_window() -> None:
    """Test windows are fixed: they end at multiples of the period."""
    number, end = get_window(
        timedelta(minutes=1), datetime(2026, 10, 14, 9, 0, 59, tzinfo=UTC)
    )
    assert end == datetime(2026, 10, 14, 9, 1, tzinfo=UTC)
    assert get_window(timedelta(minutes=1), end) == (
        number + 1,
        datetime(2026, 10, 14, 9, 2, tzinfo=UTC),
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_postgres_rate_limiter_429(
    async_db_session: AsyncSession, start_of_minute: datetime
) -> None:
    """Test a key over its limit gets a 429 saying how long to wait."""
    limiter = PostgresRateLimiter(async_db_session)
    search = RateLimit("search", 2, timedelta(minutes=1))
    for _ in range(2):
        await limiter.hit(search, "203.0.113.7")
    with pytest.raises(TooManyRequestsHTTPException) as exc_info:
        await limiter.hit(search, "203.0.113.7")
    assert exc_info.value.headers == {"Retry-After": "60"}
    # Other keys and other limits have counters of their own.
    await limiter.hit(search, "198.51.100.1")
    await limiter.hit(RateLimit("export", 2, timedelta(minutes=1)), "203.0.113.7")


@pytest.mark.asyncio(loop_scope="function")
async def test_postgres_rate_limiter_next_window(
    async_db_session: AsyncSession,
    start_of_minute: datetime,
    time_machine: TimeMachineFixture,
) -> None:
    """Test the count starts again in the next window."""
    limiter = PostgresRateLimiter(async_db_session)
    search = RateLimit("search", 1, timedelta(minutes=1))
    await limiter.hit(search, "203.0.113.7")
    time_machine.shift(timedelta(minutes=1))
    await limiter.hit(search, "203.0.113.7")


@pytest.mark.asyncio(loop_scope="function")
async def test_postgres_rate_limiter_purge_expired(
    async_db_session: AsyncSession,
    start_of_minute: datetime,
    time_machine: TimeMachineFixture,
) -> None:
    """Test only the counters of past windows are deleted."""
    limiter = PostgresRateLimiter(async_db_session)
    search = RateLimit("search", 5, timedelta(minutes=1))
    for ip in ("203.0.113.7", "198.51.100.1"):
        await limiter.hit(search, ip)
    time_machine.shift(timedelta(minutes=1))
    await limiter.hit(search, "203.0.113.7")
    assert await PostgresRateLimiter.purge_expired(async_db_session) == 2
    assert await PostgresRateLimiter.purge_expired(async_db_session) == 0
