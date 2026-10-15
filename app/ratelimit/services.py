"""The ratelimit package services."""

import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import TooManyRequestsHTTPException
from app.ratelimit.models import RateLimitCounter


@dataclass(frozen=True)
class RateLimit:
    """At most ``limit`` requests per ``period``, counted per key."""

    name: str
    limit: int
    period: timedelta


class RateLimiter(Protocol):
    """Count requests and reject the ones over a limit."""

    async def hit(self, rate_limit: RateLimit, key: str) -> None:
        """Count a request for a key; raise a 429 if it exceeds the limit."""
        ...  # pragma: no cover


def get_window(period: timedelta, now: datetime) -> tuple[int, datetime]:
    """Return the number of the fixed time window ``now`` falls in, and its end."""
    seconds = period.total_seconds()
    number = int(now.timestamp() // seconds)
    return number, datetime.fromtimestamp((number + 1) * seconds, UTC)


class PostgresRateLimiter:
    """
    A rate limiter with fixed-window counters in PostgreSQL.

    Why: an atomic upsert counts each request, so concurrent requests on several
    workers or containers never lose a count, with no other service to run.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the instance."""
        self.session = session

    async def hit(self, rate_limit: RateLimit, key: str) -> None:
        """Count a request for a key; raise a 429 if it exceeds the limit."""
        now = datetime.now(UTC)
        window, window_end = get_window(rate_limit.period, now)
        key_hash = hashlib.sha256(
            f"{rate_limit.name}:{key}:{window}".encode()
        ).hexdigest()
        result = await self.session.exec(
            insert(RateLimitCounter)
            .values(key_hash=key_hash, count=1, datetime_expires=window_end)
            .on_conflict_do_update(
                index_elements=[col(RateLimitCounter.key_hash)],
                set_={"count": col(RateLimitCounter.count) + 1},
            )
            .returning(col(RateLimitCounter.count))
        )
        count = result.scalar_one()
        # Why: committed at once, so the request counts even if it then fails
        # (a wrong password is exactly the request to count).
        await self.session.commit()
        if count > rate_limit.limit:
            retry_after = math.ceil((window_end - now).total_seconds())
            raise TooManyRequestsHTTPException(
                message="Too many requests: try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    @staticmethod
    async def purge_expired(session: AsyncSession) -> int:
        """Delete the counters of past windows, returning how many were deleted."""
        result = await session.exec(
            delete(RateLimitCounter).where(
                col(RateLimitCounter.datetime_expires) <= datetime.now(UTC)
            )
        )
        await session.commit()
        return result.rowcount
