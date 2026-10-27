"""The analytics package dependencies tests."""

import pytest
from fastapi import Depends, FastAPI, status
from inline_snapshot import snapshot

from app.analytics.dependencies import get_analytics, require_feature_flag
from app.analytics.services import DisabledAnalytics, PostHogAnalytics, get_posthog
from app.core.config import settings
from app.users.models import User
from tests.pytest_plugins.analytics import FakeAnalytics
from tests.utils import AsyncClient


def test_get_analytics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the analytics send to PostHog only when it is configured."""
    assert isinstance(get_analytics(), DisabledAnalytics)
    monkeypatch.setattr(settings, "POSTHOG_API_KEY", "phc_test")
    get_posthog.cache_clear()
    assert isinstance(get_analytics(), PostHogAnalytics)


@pytest.mark.asyncio(loop_scope="function")
async def test_require_feature_flag(
    test_app: FastAPI,
    async_client: AsyncClient,
    bob_member_user: User,
    fake_analytics: FakeAnalytics,
) -> None:
    """Test a route behind a flag exists only for the users who have the flag."""

    async def beta_route() -> dict[str, str]:
        """Answer from a route behind a flag."""
        return {"hello": "beta"}

    test_app.add_api_route(
        "/api/beta/", beta_route, dependencies=[Depends(require_feature_flag("beta"))]
    )
    async_client.login(bob_member_user)
    response = await async_client.get("/api/beta/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == snapshot(
        {"detail": {"message": "Not Found", "errorCode": "NOT_FOUND"}}
    )
    fake_analytics.enabled_flags.add("beta")
    response = await async_client.get("/api/beta/")
    assert response.status_code == status.HTTP_200_OK
