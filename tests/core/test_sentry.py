"""The core Sentry integration tests."""

import sys
from types import SimpleNamespace

import pytest
import structlog
from pytest_mock import MockerFixture

from app.core.config import Settings
from app.core.sentry import add_request_id_to_sentry_event, init_sentry


def test_add_request_id_to_sentry_event() -> None:
    """Test Sentry events are tagged with the request id, when there is one."""
    with structlog.contextvars.bound_contextvars(request_id="abc"):
        assert add_request_id_to_sentry_event({"tags": {"a": "b"}}, {}) == {
            "tags": {"a": "b", "request_id": "abc"}
        }
    structlog.contextvars.clear_contextvars()
    assert add_request_id_to_sentry_event({}, {}) == {}


def test_init_sentry(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Sentry starts with the version, the sample rate and no personal data."""
    sentry_sdk = SimpleNamespace(init=mocker.Mock())
    monkeypatch.setitem(sys.modules, "sentry_sdk", sentry_sdk)
    app_settings = Settings(SENTRY_TRACES_SAMPLE_RATE=0.25)
    assert init_sentry(app_settings) is True
    sentry_sdk.init.assert_called_once_with(
        release=app_settings.VERSION,
        traces_sample_rate=0.25,
        send_default_pii=False,
        before_send=add_request_id_to_sentry_event,
    )


def test_init_sentry_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the app starts without Sentry where the SDK is not installed."""
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    assert init_sentry(Settings()) is False
