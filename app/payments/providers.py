"""The payments package providers: what the app needs from a payment provider."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.payments.enums import SubscriptionStatus
from app.users.models import User


class PaymentProviderUnavailableError(Exception):
    """The provider cannot be reached, or cannot answer right now."""


class WebhookSignatureError(Exception):
    """The webhook does not come from the provider."""


class WebhookPayloadError(Exception):
    """The webhook comes from the provider, but cannot be read."""


@dataclass(frozen=True)
class SubscriptionSnapshot:
    """A subscription as the provider sees it at a point in time."""

    provider_id: str
    user_id: UUID | None
    product_id: str
    status: SubscriptionStatus
    current_period_end: datetime | None
    cancel_at_period_end: bool
    datetime_modified: datetime


@dataclass(frozen=True)
class ProviderEvent:
    """A verified webhook: its id, its type and the subscription it is about."""

    id: str
    type: str
    subscription: SubscriptionSnapshot | None


class PaymentProvider(Protocol):
    """A payment provider that sells subscriptions."""

    product_ids: frozenset[str]

    async def create_checkout(self, product_id: str, user: User) -> str:
        """Return the URL of a page where the user subscribes to a product."""
        ...  # pragma: no cover

    async def create_portal_session(self, user: User) -> str:
        """Return the URL of a page where the user manages their subscriptions."""
        ...  # pragma: no cover

    def parse_webhook(self, body: bytes, headers: Mapping[str, str]) -> ProviderEvent:
        """Verify a webhook and return its event."""
        ...  # pragma: no cover

    async def aclose(self) -> None:
        """Release the connections to the provider."""
        ...  # pragma: no cover
