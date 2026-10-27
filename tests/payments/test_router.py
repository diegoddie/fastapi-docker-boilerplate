"""The payments package router tests."""

from datetime import datetime

import pytest
from dirty_equals import IsDatetime, IsUUID
from fastapi import status
from inline_snapshot import snapshot
from polar.base import PolarServerError
from pytest_mock import MockType
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.payments.models import Subscription
from app.ratelimit.models import RateLimitCounter
from app.users.models import User
from tests.factories.payments import SubscriptionFactory
from tests.utils import AsyncClient


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/api/v1/payments/checkout/"),
        ("post", "/api/v1/payments/portal-session/"),
        ("get", "/api/v1/payments/subscription/"),
    ],
    ids=["create_checkout", "create_portal_session", "list_subscriptions"],
)
async def test_route_401(async_client: AsyncClient, method: str, url: str) -> None:
    """Test that every payment route but the webhook requires authentication."""
    response = await getattr(async_client, method)(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_route_201(
    async_client: AsyncClient,
    bob_member_user: User,
    polar_provider: object,
    polar_client: MockType,
    polar_product_id: str,
) -> None:
    """Test the create checkout route 201: a Polar checkout for Bob as customer."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/payments/checkout/", json={"productId": polar_product_id}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"url": "https://sandbox.polar.sh/checkout/polar_c_test"}
    polar_client.checkouts.create.assert_awaited_once_with(
        products=[polar_product_id],
        external_customer_id=str(bob_member_user.id),
        customer_email="bob@example.com",
        success_url=f"{settings.FRONTEND_URL}/billing/success?checkout_id={{CHECKOUT_ID}}",
        return_url=f"{settings.FRONTEND_URL}/billing",
    )
    # The connection went back to the pool before Polar was called.
    assert polar_client.in_transaction == [False]


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_route_403_email_not_verified(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    polar_provider: object,
    polar_product_id: str,
) -> None:
    """Test the create checkout route 403 for an address nobody proved."""
    bob_member_user.datetime_email_verified = None
    async_db_session.add(bob_member_user)
    await async_db_session.commit()
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/payments/checkout/", json={"productId": polar_product_id}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["errorCode"] == "EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_route_404_payments_disabled(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    polar_product_id: str,
) -> None:
    """Test the create checkout route 404 without Polar, uncounted."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/payments/checkout/", json={"productId": polar_product_id}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "Payments are not enabled",
                "errorCode": "PAYMENTS_DISABLED",
            }
        }
    )
    assert (await async_db_session.exec(select(RateLimitCounter))).all() == []


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_route_409_subscription_exists(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_pro_subscription: Subscription,
    polar_provider: object,
    polar_product_id: str,
) -> None:
    """Test the create checkout route 409 for a user who already subscribed."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/payments/checkout/", json={"productId": polar_product_id}
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"]["errorCode"] == "SUBSCRIPTION_EXISTS"


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_route_422_unknown_product(
    async_client: AsyncClient, bob_member_user: User, polar_provider: object
) -> None:
    """Test the create checkout route 422 for a product that is not for sale."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/payments/checkout/", json={"productId": "another-product"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"]["errorCode"] == "UNKNOWN_PRODUCT"


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_route_429(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    bob_member_user: User,
    polar_provider: object,
    polar_product_id: str,
    start_of_minute: datetime,
) -> None:
    """Test the checkouts and portal sessions of a user are limited per hour."""
    monkeypatch.setattr(settings, "RATE_LIMIT_PAYMENTS_REQUESTS_PER_HOUR", 1)
    async_client.login(bob_member_user)
    payload = {"productId": polar_product_id}
    response = await async_client.post("/api/v1/payments/checkout/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    response = await async_client.post("/api/v1/payments/checkout/", json=payload)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_route_503(
    async_client: AsyncClient,
    bob_member_user: User,
    polar_provider: object,
    polar_client: MockType,
    polar_product_id: str,
) -> None:
    """Test the create checkout route 503 when Polar cannot answer."""
    polar_client.checkouts.create.side_effect = PolarServerError(502, "Bad Gateway")
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/payments/checkout/", json={"productId": polar_product_id}
    )
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "The payment service is unavailable, try again later",
                "errorCode": "PAYMENTS_UNAVAILABLE",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_create_portal_session_route_201(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_pro_subscription: Subscription,
    polar_provider: object,
    polar_client: MockType,
) -> None:
    """Test the create portal session route 201: Bob's page at Polar."""
    async_client.login(bob_member_user)
    response = await async_client.post("/api/v1/payments/portal-session/")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"url": "https://sandbox.polar.sh/acme/portal?token=test"}
    polar_client.customer_sessions.create.assert_awaited_once_with(
        external_customer_id=str(bob_member_user.id),
        return_url=f"{settings.FRONTEND_URL}/billing",
    )
    assert polar_client.in_transaction == [False]


@pytest.mark.asyncio(loop_scope="function")
async def test_create_portal_session_route_404_no_subscription(
    async_client: AsyncClient, bob_member_user: User, polar_provider: object
) -> None:
    """Test the create portal session route 404 for a user who never subscribed."""
    async_client.login(bob_member_user)
    response = await async_client.post("/api/v1/payments/portal-session/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"]["errorCode"] == "SUBSCRIPTION_NOT_FOUND"


@pytest.mark.asyncio(loop_scope="function")
async def test_list_subscriptions_route_200(
    async_client: AsyncClient,
    bob_member_user: User,
    alice_admin_user: User,
    bob_pro_subscription: Subscription,
    polar_product_id: str,
) -> None:
    """Test the list subscriptions route 200: only your own subscriptions."""
    await SubscriptionFactory.create_async(
        user_id=alice_admin_user.id, product_id=polar_product_id
    )
    async_client.login(bob_member_user)
    response = await async_client.get("/api/v1/payments/subscription/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == snapshot(
        {
            "items": [
                {
                    "id": IsUUID,
                    "productId": "8a1c7a43-6e8c-4f1d-9b0e-3c6f2d1e5a10",
                    "status": "active",
                    "currentPeriodEnd": "2026-11-20T00:00:00Z",
                    "cancelAtPeriodEnd": False,
                    "datetimeCreated": IsDatetime(iso_string=True),
                }
            ],
            "total": 1,
            "page": 1,
            "size": 50,
            "pages": 1,
        }
    )
