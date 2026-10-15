"""The ratelimit package dependencies."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.database import AsyncDBSession
from app.ratelimit.services import PostgresRateLimiter, RateLimiter


def get_rate_limiter(session: AsyncDBSession) -> RateLimiter:
    """Return the rate limiter, sharing the request's database session."""
    return PostgresRateLimiter(session)


def get_client_ip(request: Request) -> str:
    """
    Return the IP address of the client.

    Why: behind a proxy this is the proxy's address, unless the proxy is trusted
    (``FORWARDED_ALLOW_IPS``): then uvicorn reads it from ``X-Forwarded-For``.
    """
    return request.client.host if request.client else "unknown"


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
ClientIP = Annotated[str, Depends(get_client_ip)]
