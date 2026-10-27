"""The payments package dependencies."""

from datetime import timedelta
from functools import cache
from typing import Annotated

from fastapi import Depends
from polar.v2026_10 import PolarAsync

from app.auth.dependencies import AuthenticatedUser
from app.core.config import settings
from app.core.exceptions import NotFoundHTTPException
from app.payments.constants import PAYMENTS_REQUESTS_RATE_LIMIT
from app.payments.polar_provider import PolarPaymentProvider
from app.payments.providers import PaymentProvider
from app.ratelimit.dependencies import RateLimiterDep
from app.ratelimit.services import RateLimit


@cache
def build_payment_provider() -> PaymentProvider | None:
    """Return the payment provider, created once; None when not configured."""
    if settings.POLAR_ACCESS_TOKEN is None or settings.POLAR_WEBHOOK_SECRET is None:
        return None
    return PolarPaymentProvider(
        PolarAsync(
            settings.POLAR_ACCESS_TOKEN.get_secret_value(),
            environment=settings.POLAR_ENVIRONMENT,
            timeout=settings.POLAR_TIMEOUT_SECONDS,
        ),
        webhook_secret=settings.POLAR_WEBHOOK_SECRET.get_secret_value(),
        product_ids=frozenset(settings.POLAR_PRODUCT_IDS),
    )


def get_payment_provider() -> PaymentProvider:
    """Return the payment provider, or answer 404 when payments are off."""
    provider = build_payment_provider()
    if provider is None:
        raise NotFoundHTTPException(
            message="Payments are not enabled", error_code="PAYMENTS_DISABLED"
        )
    return provider


async def close_payments() -> None:
    """Release the connections to the payment provider, at shutdown."""
    provider = build_payment_provider()
    if provider is not None:
        await provider.aclose()


async def limit_payments_requests(
    user: AuthenticatedUser, limiter: RateLimiterDep
) -> None:
    """Limit the checkouts and portal sessions each user creates."""
    await limiter.hit(
        RateLimit(
            PAYMENTS_REQUESTS_RATE_LIMIT,
            settings.RATE_LIMIT_PAYMENTS_REQUESTS_PER_HOUR,
            timedelta(hours=1),
        ),
        str(user.id),
    )


PaymentProviderDep = Annotated[PaymentProvider, Depends(get_payment_provider)]
