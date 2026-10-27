"""The payments package services."""

from collections.abc import Awaitable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, delete, exists, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

# copier:posthog:start
from app.analytics.constants import SUBSCRIPTION_ENDED, SUBSCRIPTION_STARTED
from app.analytics.services import Analytics

# copier:posthog:end
from app.core.exceptions import (
    BadRequestHTTPException,
    ConflictHTTPException,
    ForbiddenHTTPException,
    NotFoundHTTPException,
    ServiceUnavailableHTTPException,
    UnprocessableHTTPException,
)
from app.payments.constants import ACCESS_STATUSES, WEBHOOK_EVENT_RETENTION_DAYS
from app.payments.models import Subscription, WebhookEvent
from app.payments.providers import (
    PaymentProvider,
    PaymentProviderUnavailableError,
    SubscriptionSnapshot,
    WebhookPayloadError,
    WebhookSignatureError,
)
from app.payments.schemas import CheckoutPublicSchemaCreate
from app.users.enums import Group
from app.users.models import User

logger = structlog.get_logger(__name__)


async def _call_provider(call: Awaitable[str]) -> str:
    """Return the URL the provider answers with; 503 when it cannot answer."""
    try:
        return await call
    except PaymentProviderUnavailableError as e:
        logger.warning("payment_provider_unavailable")
        raise ServiceUnavailableHTTPException(
            message="The payment service is unavailable, try again later",
            error_code="PAYMENTS_UNAVAILABLE",
        ) from e


class PaymentService:
    """The subscriptions of the users."""

    @staticmethod
    async def has_access(user_id: UUID, session: AsyncSession) -> bool:
        """Tell if a user has a subscription that gives access."""
        return bool(
            await session.scalar(
                select(
                    exists().where(
                        col(Subscription.user_id) == user_id,
                        col(Subscription.status).in_(ACCESS_STATUSES),
                    )
                )
            )
        )

    @staticmethod
    async def create_checkout(
        payload: CheckoutPublicSchemaCreate,
        session: AsyncSession,
        user: User,
        provider: PaymentProvider,
    ) -> str:
        """Return the URL of a checkout of a product, for a user without access."""
        if not user.is_email_verified:
            # Why: the customer is created with this address; it must be theirs.
            raise ForbiddenHTTPException(
                message="Verify your email address before subscribing.",
                error_code="EMAIL_NOT_VERIFIED",
            )
        if payload.product_id not in provider.product_ids:
            raise UnprocessableHTTPException(
                message="This product cannot be bought.", error_code="UNKNOWN_PRODUCT"
            )
        if await PaymentService.has_access(user.id, session):
            raise ConflictHTTPException(
                message="You already have an active subscription.",
                error_code="SUBSCRIPTION_EXISTS",
            )
        # Why: the provider takes a while; meanwhile the connection is back in the pool.
        await session.commit()
        return await _call_provider(provider.create_checkout(payload.product_id, user))

    @staticmethod
    async def create_portal_session(
        session: AsyncSession, user: User, provider: PaymentProvider
    ) -> str:
        """Return the URL of the page where the user manages their subscriptions."""
        has_subscription = await session.scalar(
            select(exists().where(col(Subscription.user_id) == user.id))
        )
        if not has_subscription:
            raise NotFoundHTTPException(
                message="You have no subscription yet.",
                error_code="SUBSCRIPTION_NOT_FOUND",
            )
        await session.commit()
        return await _call_provider(provider.create_portal_session(user))

    @staticmethod
    def list_query(user: User) -> SelectOfScalar[Subscription]:
        """Return the query of the user's subscriptions, the latest first."""
        return (
            select(Subscription)
            .where(col(Subscription.user_id) == user.id)
            .order_by(col(Subscription.datetime_created).desc(), col(Subscription.id))
        )

    @staticmethod
    async def process_webhook(
        body: bytes,
        headers: Mapping[str, str],
        session: AsyncSession,
        provider: PaymentProvider,
        analytics: Analytics,  # copier:posthog
    ) -> None:
        """Apply a webhook of the provider, once, whatever the order of arrival."""
        try:
            event = provider.parse_webhook(body, headers)
        except WebhookSignatureError as e:
            raise ForbiddenHTTPException(
                message="Invalid webhook signature.",
                error_code="INVALID_WEBHOOK_SIGNATURE",
            ) from e
        except WebhookPayloadError as e:
            raise BadRequestHTTPException(
                message="Invalid webhook payload.", error_code="INVALID_WEBHOOK_PAYLOAD"
            ) from e
        log = logger.bind(event_id=event.id, event_type=event.type)
        # Why: the provider retries until it gets a 2xx, so the same event can
        # arrive twice; its id is recorded in the same transaction as its effect.
        recorded = await session.scalar(
            insert(WebhookEvent)
            .values(provider_event_id=event.id, event_type=event.type)
            .on_conflict_do_nothing(
                index_elements=[col(WebhookEvent.provider_event_id)]
            )
            .returning(col(WebhookEvent.id))
        )
        snapshot = event.subscription
        if recorded is None or snapshot is None:
            log.info("payment_webhook_skipped", duplicate=recorded is None)
            await session.commit()
            return
        user = await session.get(User, snapshot.user_id) if snapshot.user_id else None
        if user is None:
            # Why: acknowledged, or the provider would retry for days in vain.
            log.warning(
                "payment_webhook_unknown_customer", subscription_id=snapshot.provider_id
            )
            await session.commit()
            return
        await PaymentService._save_snapshot(snapshot, user, session)
        had_access = Group.PRO in user.groups
        has_access = await PaymentService.has_access(user.id, session)
        # Why: the group is a copy of the table, recomputed on every change.
        user.groups = [group for group in user.groups if group != Group.PRO] + (
            [Group.PRO] if has_access else []
        )
        session.add(user)
        await session.commit()
        log.info(
            "payment_webhook_applied",
            subscription_id=snapshot.provider_id,
            status=snapshot.status,
            user_id=str(user.id),
            has_access=has_access,
        )
        # copier:posthog:start
        if has_access != had_access:
            analytics.capture(
                SUBSCRIPTION_STARTED if has_access else SUBSCRIPTION_ENDED,
                user.id,
                {"product_id": snapshot.product_id},
            )
        # copier:posthog:end

    @staticmethod
    async def _save_snapshot(
        snapshot: SubscriptionSnapshot, user: User, session: AsyncSession
    ) -> None:
        """Save a snapshot of a subscription, unless a newer one is saved already."""
        values = {
            "user_id": user.id,
            "product_id": snapshot.product_id,
            "status": snapshot.status,
            "current_period_end": snapshot.current_period_end,
            "cancel_at_period_end": snapshot.cancel_at_period_end,
            "datetime_provider_modified": snapshot.datetime_modified,
        }
        statement = insert(Subscription).values(
            provider_id=snapshot.provider_id, **values
        )
        await session.exec(
            statement.on_conflict_do_update(
                index_elements=[col(Subscription.provider_id)],
                set_=values | {"datetime_updated": datetime.now(UTC)},
                # Why: last write wins by the provider's clock, not by arrival.
                where=col(Subscription.datetime_provider_modified)
                < statement.excluded.datetime_provider_modified,
            )
        )

    @staticmethod
    async def purge_webhook_events(session: AsyncSession) -> int:
        """Delete the records of old webhooks, returning how many were deleted."""
        result = await session.exec(
            delete(WebhookEvent).where(
                col(WebhookEvent.datetime_created)
                < datetime.now(UTC) - timedelta(days=WEBHOOK_EVENT_RETENTION_DAYS)
            )
        )
        await session.commit()
        return result.rowcount
