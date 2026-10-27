"""
The analytics fixtures.

No test ever calls PostHog:

- ``no_posthog`` (automatic) clears its key, so the real client is never built
  and the routes get analytics that send nothing;
- ``fake_analytics`` replaces the analytics with ``FakeAnalytics``, which
  records the events and turns on the flags the test lists.
"""

from collections.abc import Iterator, Mapping
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI

from app.analytics.dependencies import get_analytics
from app.analytics.services import get_posthog
from app.core.config import settings


class FakeAnalytics:
    """Analytics that record the events and turn on the listed flags."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self.events: list[tuple[str, UUID, dict[str, Any]]] = []
        self.enabled_flags: set[str] = set()

    def capture(
        self, event: str, user_id: UUID, properties: Mapping[str, Any] | None = None
    ) -> None:
        """Record an event."""
        self.events.append((event, user_id, dict(properties or {})))

    async def is_enabled(self, flag: str, user_id: UUID) -> bool:
        """Tell if the test turned the flag on."""
        return flag in self.enabled_flags


@pytest.fixture(autouse=True)
def no_posthog(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear the PostHog key, so no test ever sends anything to PostHog."""
    monkeypatch.setattr(settings, "POSTHOG_API_KEY", None)
    get_posthog.cache_clear()
    yield
    get_posthog.cache_clear()


@pytest.fixture
def fake_analytics(test_app: FastAPI) -> FakeAnalytics:
    """Replace the analytics with a fake that records the events."""
    fake = FakeAnalytics()
    test_app.dependency_overrides[get_analytics] = lambda: fake
    return fake
