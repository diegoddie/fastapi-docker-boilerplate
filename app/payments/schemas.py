"""The payments package schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.commons.schemas import BasePublicSchema
from app.payments.enums import SubscriptionStatus


class CheckoutPublicSchemaCreate(BasePublicSchema):
    """The checkout public schema create."""

    product_id: str = Field(min_length=1, max_length=100)


class RedirectPublicSchemaResponse(BasePublicSchema):
    """A page of the provider to send the customer to."""

    url: str


class SubscriptionPublicSchemaResponse(BasePublicSchema):
    """The subscription public schema response."""

    id: UUID
    product_id: str
    status: SubscriptionStatus
    current_period_end: datetime | None
    cancel_at_period_end: bool
    datetime_created: datetime
