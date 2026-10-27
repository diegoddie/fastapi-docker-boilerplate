"""
The payments fixtures.

No test ever calls Polar:

- ``no_polar`` (automatic) clears its token and webhook secret, so the payment
  routes answer 404 unless a test sets a provider up;
- ``polar_client`` replaces Polar's API: checkouts and customer sessions return
  fixed URLs, and record whether a database transaction was open meanwhile;
- ``polar_provider`` is the real ``PolarPaymentProvider`` on that client, with
  a known webhook secret, used by the routes;
- ``polar_webhook`` signs a payload like Polar does (Standard Webhooks);
- ``polar_subscription`` builds the payload of a subscription event, with the
  fields Polar sends, most of which the app ignores.
"""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable, Iterator
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from polar.v2026_10 import PolarAsync
from pytest_mock import MockerFixture, MockType
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.payments.dependencies import build_payment_provider, get_payment_provider
from app.payments.models import Subscription
from app.payments.polar_provider import PolarPaymentProvider
from app.users.models import User
from tests.factories.payments import SubscriptionFactory


@pytest.fixture(autouse=True)
def no_polar(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear the Polar token and webhook secret, so no test ever calls Polar."""
    monkeypatch.setattr(settings, "POLAR_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "POLAR_WEBHOOK_SECRET", None)
    build_payment_provider.cache_clear()
    yield
    build_payment_provider.cache_clear()


@pytest.fixture
def polar_product_id() -> str:
    """Return the id of the Pro product, the one users may buy."""
    return "8a1c7a43-6e8c-4f1d-9b0e-3c6f2d1e5a10"


@pytest.fixture
def polar_client(mocker: MockerFixture, async_db_session: AsyncSession) -> MockType:
    """Return a fake of Polar's API that records the calls."""
    client = mocker.MagicMock()
    client.in_transaction = []

    async def create_checkout(**kwargs: Any) -> SimpleNamespace:
        client.in_transaction.append(async_db_session.in_transaction())
        return SimpleNamespace(url="https://sandbox.polar.sh/checkout/polar_c_test")

    async def create_session(**kwargs: Any) -> SimpleNamespace:
        client.in_transaction.append(async_db_session.in_transaction())
        return SimpleNamespace(
            customer_portal_url="https://sandbox.polar.sh/acme/portal?token=test"
        )

    client.checkouts.create = mocker.AsyncMock(side_effect=create_checkout)
    client.customer_sessions.create = mocker.AsyncMock(side_effect=create_session)
    return cast(MockType, client)


@pytest.fixture
def polar_provider(
    test_app: FastAPI, polar_client: MockType, polar_product_id: str
) -> PolarPaymentProvider:
    """Return the Polar provider on the fake API, used by the routes."""
    provider = PolarPaymentProvider(
        cast(PolarAsync, polar_client),
        webhook_secret="whsec_dGVzdC13ZWJob29rLXNlY3JldA==",
        product_ids=frozenset({polar_product_id}),
    )
    test_app.dependency_overrides[get_payment_provider] = lambda: provider
    return provider


@pytest.fixture
def polar_webhook(
    polar_provider: PolarPaymentProvider,
) -> Callable[..., tuple[bytes, dict[str, str]]]:
    """Return a function that signs a payload the way Polar does."""

    def sign(
        payload: dict[str, Any], event_id: str | None = None, secret: str | None = None
    ) -> tuple[bytes, dict[str, str]]:
        """Return the body and the headers of a webhook."""
        body = json.dumps(payload).encode()
        webhook_id = event_id or f"msg_{uuid4().hex}"
        timestamp = str(int(time.time()))
        key = (secret or polar_provider.webhook_secret).encode()
        digest = hmac.new(
            key, f"{webhook_id}.{timestamp}.".encode() + body, hashlib.sha256
        ).digest()
        return body, {
            "content-type": "application/json",
            "webhook-id": webhook_id,
            "webhook-timestamp": timestamp,
            "webhook-signature": f"v1,{base64.b64encode(digest).decode()}",
        }

    return sign


@pytest.fixture
def polar_subscription(polar_product_id: str) -> Callable[..., dict[str, Any]]:
    """Return a function that builds the payload of a subscription event."""

    def build(
        event_type: str,
        user_id: UUID | None,
        status: str = "active",
        modified_at: datetime | None = None,
        cancel_at_period_end: bool = False,
        subscription_id: str = "4f0a9a1e-2b7c-4d3e-8f61-5a9c0e7d2b34",
    ) -> dict[str, Any]:
        """Return a subscription event, shaped like Polar's (API 2026-10)."""
        customer_id = "c3b2a190-8f7e-4d6c-b5a4-938271605f4e"
        return {
            "type": event_type,
            "timestamp": "2026-10-20T10:00:05Z",
            "api_version": "2026-10",
            "data": {
                "created_at": "2026-10-20T10:00:00Z",
                "modified_at": modified_at.isoformat() if modified_at else None,
                "id": subscription_id,
                "amount": 900,
                "currency": "eur",
                "recurring_interval": "month",
                "recurring_interval_count": 1,
                "status": status,
                "current_period_start": "2026-10-20T10:00:00Z",
                "current_period_end": "2026-11-20T10:00:00Z",
                "cancel_at_period_end": cancel_at_period_end,
                "canceled_at": None,
                "started_at": "2026-10-20T10:00:00Z",
                "ends_at": None,
                "ended_at": None,
                "customer_id": customer_id,
                "product_id": polar_product_id,
                "discount_id": None,
                "checkout_id": "b7e1c2d3-4a5b-4c6d-8e9f-0a1b2c3d4e5f",
                "metadata": {},
                "customer": {
                    "id": customer_id,
                    "created_at": "2026-10-20T09:59:00Z",
                    "external_id": str(user_id) if user_id else None,
                    "email": "bob@example.com",
                    "email_verified": True,
                    "name": "Bob Member",
                    "metadata": {},
                },
                "product": {
                    "id": polar_product_id,
                    "name": "Pro",
                    "is_recurring": True,
                },
                "prices": [],
                "meters": [],
            },
        }

    return build


@pytest_asyncio.fixture(loop_scope="function")
async def bob_pro_subscription(
    seed_factories: None, bob_member_user: User, polar_product_id: str
) -> Subscription:
    """Return Bob's active Pro subscription."""
    return await SubscriptionFactory.create_async(
        user_id=bob_member_user.id, product_id=polar_product_id
    )
