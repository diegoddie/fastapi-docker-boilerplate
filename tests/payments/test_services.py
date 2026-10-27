"""The payments package services tests."""

from datetime import timedelta

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from time_machine import TimeMachineFixture

from app.payments.enums import SubscriptionStatus
from app.payments.models import WebhookEvent
from app.payments.services import PaymentService
from app.users.models import User
from tests.factories.payments import SubscriptionFactory


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("status", list(SubscriptionStatus))
async def test_has_access(
    seed_factories: None,
    async_db_session: AsyncSession,
    bob_member_user: User,
    polar_product_id: str,
    status: SubscriptionStatus,
) -> None:
    """Test which statuses give access: paid, on trial, or a payment being retried."""
    await SubscriptionFactory.create_async(
        user_id=bob_member_user.id, product_id=polar_product_id, status=status
    )
    assert await PaymentService.has_access(bob_member_user.id, async_db_session) is (
        status in {"active", "trialing", "past_due"}
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_purge_webhook_events(
    async_db_session: AsyncSession, time_machine: TimeMachineFixture
) -> None:
    """Test the records of webhooks older than 30 days are deleted."""
    time_machine.move_to("2026-10-01T10:00:00Z", tick=False)
    async_db_session.add(WebhookEvent(provider_event_id="msg_old", event_type="t"))
    await async_db_session.commit()
    time_machine.shift(timedelta(days=29))
    async_db_session.add(WebhookEvent(provider_event_id="msg_recent", event_type="t"))
    await async_db_session.commit()
    time_machine.shift(timedelta(days=2))
    assert await PaymentService.purge_webhook_events(async_db_session) == 1
    assert (
        await async_db_session.exec(select(WebhookEvent.provider_event_id))
    ).all() == ["msg_recent"]
