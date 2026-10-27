"""The analytics package dependencies."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from app.analytics.services import (
    Analytics,
    DisabledAnalytics,
    PostHogAnalytics,
    get_posthog,
)
from app.auth.dependencies import AuthenticatedUser
from app.core.exceptions import NotFoundHTTPException


def get_analytics() -> Analytics:
    """Return the analytics: PostHog when configured, otherwise none."""
    client = get_posthog()
    return DisabledAnalytics() if client is None else PostHogAnalytics(client)


AnalyticsDep = Annotated[Analytics, Depends(get_analytics)]


def require_feature_flag(flag: str) -> Callable[..., Awaitable[None]]:
    """Return a dependency that hides a route from the users without a flag."""

    async def check_feature_flag(
        user: AuthenticatedUser, analytics: AnalyticsDep
    ) -> None:
        """Answer 404 when the flag is off, as if the route did not exist."""
        if not await analytics.is_enabled(flag, user.id):
            raise NotFoundHTTPException(message="Not Found", error_code="NOT_FOUND")

    return check_feature_flag
