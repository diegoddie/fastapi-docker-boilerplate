"""The analytics package services."""

from collections.abc import Mapping
from functools import cache
from typing import Any, Protocol
from uuid import UUID

from posthog import AsyncPosthog

from app.core.config import settings


class Analytics(Protocol):
    """Product analytics: events about users, and feature flags."""

    def capture(
        self, event: str, user_id: UUID, properties: Mapping[str, Any] | None = None
    ) -> None:
        """Record an event of a user, without waiting for its delivery."""
        ...  # pragma: no cover

    async def is_enabled(self, flag: str, user_id: UUID) -> bool:
        """Tell if a feature flag is on for a user."""
        ...  # pragma: no cover


class PostHogAnalytics:
    """Analytics sent to PostHog."""

    def __init__(self, client: AsyncPosthog) -> None:
        """Initialize the instance."""
        self.client = client

    def capture(
        self, event: str, user_id: UUID, properties: Mapping[str, Any] | None = None
    ) -> None:
        """Queue an event; a background task sends the queue in batches."""
        self.client.capture(
            event, distinct_id=str(user_id), properties=dict(properties or {})
        )

    async def is_enabled(self, flag: str, user_id: UUID) -> bool:
        """
        Tell if a feature flag is on for a user, asking PostHog.

        Why: when PostHog does not answer in time, the flag is off: a feature
        behind a flag is never turned on by an outage.
        """
        flags = await self.client.evaluate_flags(str(user_id), flag_keys=[flag])
        return flags.is_enabled(flag)


class DisabledAnalytics:
    """Analytics where PostHog is not configured: nothing is sent, flags are off."""

    def capture(
        self, event: str, user_id: UUID, properties: Mapping[str, Any] | None = None
    ) -> None:
        """Drop the event."""

    async def is_enabled(self, flag: str, user_id: UUID) -> bool:
        """Tell that the flag is off."""
        return False


@cache
def get_posthog() -> AsyncPosthog | None:
    """
    Return the PostHog client, created once; None when no key is set.

    Why: created on first use, inside the event loop of the worker that uses
    it; the client is bound to that loop.
    """
    if settings.POSTHOG_API_KEY is None:
        return None
    return AsyncPosthog(
        settings.POSTHOG_API_KEY,
        host=settings.POSTHOG_HOST,
        feature_flags_request_timeout_seconds=settings.POSTHOG_FEATURE_FLAGS_TIMEOUT_SECONDS,
    )


async def close_analytics() -> None:
    """Send the events still queued, at shutdown."""
    client = get_posthog()
    if client is not None:
        await client.shutdown()
