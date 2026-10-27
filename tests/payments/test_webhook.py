"""The payments webhook tests: Polar's events, signed like Polar signs them."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi import status
from inline_snapshot import snapshot
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.payments.enums import SubscriptionStatus
from app.payments.models import Subscription, WebhookEvent
from app.users.enums import Group
from app.users.models import User
from tests.pytest_plugins.analytics import FakeAnalytics  # copier:posthog
from tests.utils import AsyncClient

Webhook = Callable[..., tuple[bytes, dict[str, str]]]
Payload = Callable[..., dict[str, Any]]


async def send(async_client: AsyncClient, body: bytes, headers: dict[str, str]) -> int:
    """Post a webhook and return the status code."""
    response = await async_client.post(
        "/api/v1/payments/webhook/", content=body, headers=headers
    )
    return response.status_code


async def bob_state(
    async_db_session: AsyncSession, bob_member_user: User
) -> tuple[list[str], list[str]]:
    """Return Bob's groups and the statuses of his subscriptions, from the database."""
    async_db_session.expunge_all()
    user = await async_db_session.get(User, bob_member_user.id)
    assert user is not None
    statuses = (
        await async_db_session.exec(
            select(Subscription.status).where(Subscription.user_id == user.id)
        )
    ).all()
    return user.groups, list(statuses)


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_202_subscription_active(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    polar_webhook: Webhook,
    polar_subscription: Payload,
) -> None:
    """Test an active subscription puts the user in the pro group."""
    body, headers = polar_webhook(
        polar_subscription("subscription.active", bob_member_user.id)
    )
    assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    assert await bob_state(async_db_session, bob_member_user) == (
        [Group.MEMBER, Group.PRO],
        [SubscriptionStatus.ACTIVE],
    )
    subscription = (await async_db_session.exec(select(Subscription))).one()
    assert subscription.model_dump(
        include={
            "provider_id",
            "product_id",
            "current_period_end",
            "cancel_at_period_end",
        }
    ) == snapshot(
        {
            "cancel_at_period_end": False,
            "product_id": "8a1c7a43-6e8c-4f1d-9b0e-3c6f2d1e5a10",
            "current_period_end": datetime(2026, 11, 20, 10, tzinfo=UTC),
            "provider_id": "4f0a9a1e-2b7c-4d3e-8f61-5a9c0e7d2b34",
        }
    )
    assert (await async_db_session.exec(select(WebhookEvent.event_type))).all() == [
        "subscription.active"
    ]


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_202_revoked(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    polar_webhook: Webhook,
    polar_subscription: Payload,
) -> None:
    """Test a subscription canceled at the end of the period keeps access until then."""
    for event_type, status_, cancel, minute in [
        ("subscription.active", "active", False, 1),
        ("subscription.canceled", "active", True, 2),
    ]:
        body, headers = polar_webhook(
            polar_subscription(
                event_type,
                bob_member_user.id,
                status=status_,
                cancel_at_period_end=cancel,
                modified_at=datetime(2026, 10, 20, 10, minute, tzinfo=UTC),
            )
        )
        assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    assert await bob_state(async_db_session, bob_member_user) == (
        [Group.MEMBER, Group.PRO],
        [SubscriptionStatus.ACTIVE],
    )
    body, headers = polar_webhook(
        polar_subscription(
            "subscription.revoked",
            bob_member_user.id,
            status="canceled",
            cancel_at_period_end=True,
            modified_at=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        )
    )
    assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    assert await bob_state(async_db_session, bob_member_user) == (
        [Group.MEMBER],
        [SubscriptionStatus.CANCELED],
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_202_out_of_order(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    polar_webhook: Webhook,
    polar_subscription: Payload,
) -> None:
    """Test an event older than the saved snapshot changes nothing."""
    newer = polar_webhook(
        polar_subscription(
            "subscription.active",
            bob_member_user.id,
            modified_at=datetime(2026, 10, 20, 10, 5, tzinfo=UTC),
        )
    )
    older = polar_webhook(
        polar_subscription(
            "subscription.created", bob_member_user.id, status="incomplete"
        )
    )
    for body, headers in (newer, older):
        assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    assert await bob_state(async_db_session, bob_member_user) == (
        [Group.MEMBER, Group.PRO],
        [SubscriptionStatus.ACTIVE],
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_202_duplicate(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    polar_webhook: Webhook,
    polar_subscription: Payload,
) -> None:
    """Test a webhook Polar sends again is applied once."""
    body, headers = polar_webhook(
        polar_subscription("subscription.active", bob_member_user.id),
        event_id="msg_retried",
    )
    assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    retry = polar_webhook(
        polar_subscription(
            "subscription.revoked",
            bob_member_user.id,
            status="canceled",
            modified_at=datetime(2026, 11, 20, tzinfo=UTC),
        ),
        event_id="msg_retried",
    )
    assert await send(async_client, *retry) == status.HTTP_202_ACCEPTED
    assert await bob_state(async_db_session, bob_member_user) == (
        [Group.MEMBER, Group.PRO],
        [SubscriptionStatus.ACTIVE],
    )


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    "user_id",
    [None, UUID("0194f8a0-2000-7000-8000-0000000000ff")],
    ids=["no_external_id", "unknown_user"],
)
async def test_webhook_route_202_unknown_customer(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    polar_webhook: Webhook,
    polar_subscription: Payload,
    log_events: Callable[[str], list[dict[str, Any]]],
    user_id: UUID | None,
) -> None:
    """Test a subscription of a customer who is no user is acknowledged and logged."""
    body, headers = polar_webhook(polar_subscription("subscription.active", user_id))
    assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    assert (await async_db_session.exec(select(Subscription))).all() == []
    assert len(log_events("payment_webhook_unknown_customer")) == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_202_other_event(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    polar_webhook: Webhook,
) -> None:
    """Test a verified event about something else is acknowledged and ignored."""
    body, headers = polar_webhook({"type": "order.paid", "data": {"id": "o_1"}})
    assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    assert (await async_db_session.exec(select(WebhookEvent.event_type))).all() == [
        "order.paid"
    ]


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_400(
    async_client: AsyncClient, polar_webhook: Webhook
) -> None:
    """Test a signed webhook that cannot be read is rejected."""
    body, headers = polar_webhook({"type": "subscription.active", "data": {}})
    response = await async_client.post(
        "/api/v1/payments/webhook/", content=body, headers=headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"]["errorCode"] == "INVALID_WEBHOOK_PAYLOAD"


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_403(
    async_client: AsyncClient,
    bob_member_user: User,
    polar_webhook: Webhook,
    polar_subscription: Payload,
) -> None:
    """Test a webhook signed with another secret is rejected."""
    body, headers = polar_webhook(
        polar_subscription("subscription.active", bob_member_user.id),
        secret="whsec_not-the-secret",
    )
    response = await async_client.post(
        "/api/v1/payments/webhook/", content=body, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "Invalid webhook signature.",
                "errorCode": "INVALID_WEBHOOK_SIGNATURE",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_404_payments_disabled(async_client: AsyncClient) -> None:
    """Test the webhook route 404 without Polar."""
    response = await async_client.post("/api/v1/payments/webhook/", content=b"{}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# copier:posthog:start
@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_route_202_analytics(
    async_client: AsyncClient,
    bob_member_user: User,
    polar_webhook: Webhook,
    polar_subscription: Payload,
    polar_product_id: str,
    fake_analytics: FakeAnalytics,
) -> None:
    """Test the start and the end of a subscription are recorded once each."""
    for event_type, status_, minute in [
        ("subscription.active", "active", 1),
        ("subscription.updated", "active", 2),
        ("subscription.revoked", "canceled", 3),
    ]:
        body, headers = polar_webhook(
            polar_subscription(
                event_type,
                bob_member_user.id,
                status=status_,
                modified_at=datetime(2026, 10, 20, 10, minute, tzinfo=UTC),
            )
        )
        assert await send(async_client, body, headers) == status.HTTP_202_ACCEPTED
    assert fake_analytics.events == [
        ("subscription_started", bob_member_user.id, {"product_id": polar_product_id}),
        ("subscription_ended", bob_member_user.id, {"product_id": polar_product_id}),
    ]


# copier:posthog:end
