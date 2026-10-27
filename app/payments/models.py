"""The payments package models."""

from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import Column
from sqlmodel import Field

from app.commons.models import BaseSQLModel, DatetimeCreatedMixin
from app.commons.types import UTCDateTime, pg_enum
from app.payments.enums import SubscriptionStatus


class Subscription(BaseSQLModel, table=True):
    """A user's subscription: a copy of the provider's, kept by its webhooks."""

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
    provider_id: str = Field(max_length=100, unique=True)
    product_id: str = Field(max_length=100)
    status: SubscriptionStatus = Field(
        sa_column=Column(pg_enum(SubscriptionStatus), nullable=False)
    )
    current_period_end: datetime | None = Field(default=None, sa_type=UTCDateTime)
    cancel_at_period_end: bool = False
    # Why: webhooks may arrive out of order; a snapshot older than this one is
    # ignored.
    datetime_provider_modified: datetime = Field(sa_type=UTCDateTime)


class WebhookEvent(DatetimeCreatedMixin, table=True):
    """A processed webhook, so that a retry of the provider is not applied twice."""

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    provider_event_id: str = Field(max_length=100, unique=True)
    event_type: str = Field(max_length=100)
