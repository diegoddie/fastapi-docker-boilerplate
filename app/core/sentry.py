"""
The core Sentry integration: unexpected errors reported to Sentry.

Why: sentry-sdk is installed only in the `remote` dependency group, so the local
and test images run without it. The DSN and the environment are read from
SENTRY_DSN and SENTRY_ENVIRONMENT; the FastAPI integration is automatic.
"""

from typing import Any

from app.core.config import Settings
from app.core.logs import get_request_id


def add_request_id_to_sentry_event(
    event: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any]:
    """Tag a Sentry event with the request id, to find the logs of its request."""
    if request_id := get_request_id():
        event.setdefault("tags", {})["request_id"] = request_id
    return event


def init_sentry(app_settings: Settings) -> bool:
    """Start reporting errors to Sentry if the SDK is installed; tell if it is."""
    try:
        import sentry_sdk
    except ModuleNotFoundError:
        return False
    sentry_sdk.init(
        release=app_settings.VERSION,
        traces_sample_rate=app_settings.SENTRY_TRACES_SAMPLE_RATE,
        # Why: no IP addresses, cookies or request bodies leave the app.
        send_default_pii=False,
        before_send=add_request_id_to_sentry_event,
    )
    return True
