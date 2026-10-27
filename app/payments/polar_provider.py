"""The payments package Polar provider."""

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from polar.base import PolarNetworkError, PolarRateLimitError, PolarServerError
from polar.v2026_10 import PolarAsync
from polar.webhooks import (
    PolarWebhookError,
    PolarWebhookUnknownTypeError,
    PolarWebhookVerificationError,
    validate_event,
)
from pydantic import BaseModel

from app.core.config import settings
from app.payments.constants import BILLING_PATH, CHECKOUT_SUCCESS_PATH
from app.payments.enums import SubscriptionStatus
from app.payments.providers import (
    PaymentProviderUnavailableError,
    ProviderEvent,
    SubscriptionSnapshot,
    WebhookPayloadError,
    WebhookSignatureError,
)
from app.users.models import User

UNAVAILABLE_ERRORS = (PolarNetworkError, PolarRateLimitError, PolarServerError)
SUBSCRIPTION_EVENT_TYPES = frozenset(
    {
        "subscription.active",
        "subscription.canceled",
        "subscription.created",
        "subscription.past_due",
        "subscription.revoked",
        "subscription.uncanceled",
        "subscription.updated",
    }
)


class PolarCustomer(BaseModel):
    """The customer of a Polar subscription: ``external_id`` is the user id."""

    external_id: str | None = None


class PolarSubscription(BaseModel):
    """The fields of a Polar subscription the app reads."""

    id: str
    status: SubscriptionStatus
    product_id: str
    current_period_end: datetime | None = None
    cancel_at_period_end: bool
    created_at: datetime
    modified_at: datetime | None = None
    customer: PolarCustomer


class PolarSubscriptionEvent(BaseModel):
    """
    A Polar webhook about a subscription.

    Why: only the fields the app uses are read, so the webhooks keep working
    when Polar adds or changes the others.
    """

    type: str
    data: PolarSubscription


def parse_user_id(external_id: str | None) -> UUID | None:
    """Return the user id a customer was created with, if any."""
    try:
        return UUID(external_id) if external_id else None
    except ValueError:
        return None


class PolarPaymentProvider:
    """Subscriptions sold with Polar (API version 2026-10)."""

    def __init__(
        self, client: PolarAsync, webhook_secret: str, product_ids: frozenset[str]
    ) -> None:
        """Initialize the instance."""
        self.client = client
        self.webhook_secret = webhook_secret
        self.product_ids = product_ids

    async def create_checkout(self, product_id: str, user: User) -> str:
        """Return the URL of a Polar checkout, for a customer that is the user."""
        try:
            checkout = await self.client.checkouts.create(
                products=[product_id],
                external_customer_id=str(user.id),
                customer_email=user.email,
                success_url=settings.FRONTEND_URL + CHECKOUT_SUCCESS_PATH,
                return_url=settings.FRONTEND_URL + BILLING_PATH,
            )
        except UNAVAILABLE_ERRORS as e:
            raise PaymentProviderUnavailableError from e
        return checkout.url

    async def create_portal_session(self, user: User) -> str:
        """Return the URL of the Polar customer portal of the user."""
        try:
            session = await self.client.customer_sessions.create(
                external_customer_id=str(user.id),
                return_url=settings.FRONTEND_URL + BILLING_PATH,
            )
        except UNAVAILABLE_ERRORS as e:
            raise PaymentProviderUnavailableError from e
        return session.customer_portal_url

    def parse_webhook(self, body: bytes, headers: Mapping[str, str]) -> ProviderEvent:
        """Verify a Polar webhook (Standard Webhooks) and return its event."""
        try:
            event = validate_event(
                body,
                dict(headers),
                self.webhook_secret,
                SUBSCRIPTION_EVENT_TYPES,
                PolarSubscriptionEvent.model_validate,
            )
        except PolarWebhookVerificationError as e:
            raise WebhookSignatureError from e
        except PolarWebhookUnknownTypeError as e:
            # Why: verified, but about something else than a subscription.
            return ProviderEvent(
                id=headers["webhook-id"], type=str(e.event_type), subscription=None
            )
        except PolarWebhookError as e:
            raise WebhookPayloadError from e
        data = event.data
        return ProviderEvent(
            id=headers["webhook-id"],
            type=event.type,
            subscription=SubscriptionSnapshot(
                provider_id=data.id,
                user_id=parse_user_id(data.customer.external_id),
                product_id=data.product_id,
                status=data.status,
                current_period_end=data.current_period_end,
                cancel_at_period_end=data.cancel_at_period_end,
                datetime_modified=data.modified_at or data.created_at,
            ),
        )

    async def aclose(self) -> None:
        """Close the HTTP client."""
        await self.client.__aexit__()
