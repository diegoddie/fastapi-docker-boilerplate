"""The analytics package services tests."""

from uuid import UUID

import pytest
from posthog import AsyncPosthog
from pytest_mock import MockerFixture

from app.analytics.services import (
    DisabledAnalytics,
    PostHogAnalytics,
    close_analytics,
    get_posthog,
)
from app.core.config import settings


def test_posthog_analytics_capture(mocker: MockerFixture) -> None:
    """Test an event is queued with the user id as the PostHog distinct id."""
    client = mocker.Mock(spec=AsyncPosthog)
    analytics = PostHogAnalytics(client)
    user_id = UUID("0194f8a0-2000-7000-8000-000000000002")
    analytics.capture("todo_created", user_id, {"priority": "high"})
    analytics.capture("email_verified", user_id)
    assert client.capture.call_args_list == [
        mocker.call(
            "todo_created", distinct_id=str(user_id), properties={"priority": "high"}
        ),
        mocker.call("email_verified", distinct_id=str(user_id), properties={}),
    ]


@pytest.mark.asyncio(loop_scope="function")
async def test_posthog_analytics_flag_off_when_unreachable() -> None:
    """Test a flag is off when PostHog cannot be reached: an outage enables nothing."""
    # Why: nothing listens on the port; send=False spares the 7 s that shutdown
    # would spend retrying to deliver the flag's usage event there.
    client = AsyncPosthog(
        "phc_test",
        host="http://127.0.0.1:9",
        send=False,
        feature_flags_request_max_retries=0,
    )
    analytics = PostHogAnalytics(client)
    assert await analytics.is_enabled("beta", UUID(int=1)) is False
    await client.shutdown()


@pytest.mark.asyncio(loop_scope="function")
async def test_posthog_analytics_flag_on(mocker: MockerFixture) -> None:
    """Test a flag is on when PostHog says so for the user."""
    client = mocker.Mock(spec=AsyncPosthog)
    flags = mocker.Mock(is_enabled=mocker.Mock(return_value=True))
    client.evaluate_flags.return_value = flags
    assert await PostHogAnalytics(client).is_enabled("beta", UUID(int=1)) is True
    client.evaluate_flags.assert_awaited_once_with(str(UUID(int=1)), flag_keys=["beta"])
    flags.is_enabled.assert_called_once_with("beta")


@pytest.mark.asyncio(loop_scope="function")
async def test_disabled_analytics() -> None:
    """Test nothing is sent and every flag is off without PostHog."""
    analytics = DisabledAnalytics()
    analytics.capture("todo_created", UUID(int=1))
    assert await analytics.is_enabled("beta", UUID(int=1)) is False


@pytest.mark.asyncio(loop_scope="function")
async def test_get_posthog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the client is built once from the settings, and closed at shutdown."""
    assert get_posthog() is None
    await close_analytics()
    monkeypatch.setattr(settings, "POSTHOG_API_KEY", "phc_test")
    get_posthog.cache_clear()
    client = get_posthog()
    assert isinstance(client, AsyncPosthog)
    assert client is get_posthog()
    assert (client.api_key, client.raw_host) == ("phc_test", "https://eu.i.posthog.com")
    await close_analytics()
