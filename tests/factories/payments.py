"""The payments test factories."""

from datetime import UTC, datetime

from app.payments.enums import SubscriptionStatus
from app.payments.models import Subscription
from tests.factories.base import BaseFactory


class SubscriptionFactory(BaseFactory[Subscription]):
    """An active subscription factory (pass the user_id and the product_id)."""

    __model__ = Subscription

    datetime_disabled = None
    status = SubscriptionStatus.ACTIVE
    cancel_at_period_end = False
    current_period_end = datetime(2026, 11, 20, tzinfo=UTC)
    datetime_provider_modified = datetime(2026, 10, 20, tzinfo=UTC)

    @classmethod
    def provider_id(cls) -> str:
        """Return a fake Polar subscription id."""
        return str(cls.__faker__.uuid4())
