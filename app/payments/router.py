"""The payments package router."""

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi_pagination import Page

from app.analytics.dependencies import AnalyticsDep  # copier:posthog
from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.commons.pagination import paginate
from app.core.database import AsyncDBSession
from app.payments.dependencies import (
    PaymentProviderDep,
    get_payment_provider,
    limit_payments_requests,
)
from app.payments.schemas import (
    CheckoutPublicSchemaCreate,
    RedirectPublicSchemaResponse,
    SubscriptionPublicSchemaResponse,
)
from app.payments.services import PaymentService

router = APIRouter()


@router.post(
    "/checkout/",
    summary="Start a checkout to subscribe to a product",
    status_code=status.HTTP_201_CREATED,
    response_model=RedirectPublicSchemaResponse,
    # Why: in this order, 401 comes first, and a project without payments
    # answers 404 before counting the request against the user's limit.
    dependencies=[
        Depends(get_current_user),
        Depends(get_payment_provider),
        Depends(limit_payments_requests),
    ],
)
async def create_checkout_route(
    payload: CheckoutPublicSchemaCreate,
    session: AsyncDBSession,
    user: AuthenticatedUser,
    provider: PaymentProviderDep,
) -> Any:
    """Create checkout route: send the user to the returned URL."""
    url = await PaymentService.create_checkout(payload, session, user, provider)
    return {"url": url}


@router.post(
    "/portal-session/",
    summary="Open the page where you manage your subscriptions",
    status_code=status.HTTP_201_CREATED,
    response_model=RedirectPublicSchemaResponse,
    dependencies=[
        Depends(get_current_user),
        Depends(get_payment_provider),
        Depends(limit_payments_requests),
    ],
)
async def create_portal_session_route(
    session: AsyncDBSession, user: AuthenticatedUser, provider: PaymentProviderDep
) -> Any:
    """Create portal session route: send the user to the returned URL."""
    url = await PaymentService.create_portal_session(session, user, provider)
    return {"url": url}


@router.get(
    "/subscription/",
    summary="Get a list of your subscriptions",
    status_code=status.HTTP_200_OK,
    response_model=Page[SubscriptionPublicSchemaResponse],
)
async def list_subscriptions_route(
    session: AsyncDBSession, user: AuthenticatedUser
) -> Any:
    """List subscriptions route."""
    return await paginate(session, PaymentService.list_query(user))


@router.post(
    "/webhook/",
    summary="Receive the webhooks of the payment provider",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_webhook_route(
    request: Request,
    session: AsyncDBSession,
    provider: PaymentProviderDep,
    analytics: AnalyticsDep,  # copier:posthog
) -> None:
    """Receive webhook route: public, the signature proves who sent it."""
    await PaymentService.process_webhook(
        await request.body(),
        request.headers,
        session,
        provider,
        analytics,  # copier:posthog
    )
