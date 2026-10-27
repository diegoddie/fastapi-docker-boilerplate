"""The payments package Polar provider tests."""

import pytest
from polar.base import PolarClientError, PolarNetworkError
from pytest_mock import MockType

from app.payments.polar_provider import PolarPaymentProvider, parse_user_id
from app.payments.providers import PaymentProviderUnavailableError
from app.users.models import User


@pytest.mark.asyncio(loop_scope="function")
async def test_create_portal_session_unavailable(
    polar_provider: PolarPaymentProvider,
    polar_client: MockType,
    bob_member_user: User,
) -> None:
    """Test a network failure means Polar is unavailable, not a bug."""
    polar_client.customer_sessions.create.side_effect = PolarNetworkError("timeout")
    with pytest.raises(PaymentProviderUnavailableError):
        await polar_provider.create_portal_session(bob_member_user)


@pytest.mark.asyncio(loop_scope="function")
async def test_create_checkout_rejected(
    polar_provider: PolarPaymentProvider,
    polar_client: MockType,
    bob_member_user: User,
) -> None:
    """Test a request Polar rejects is a bug to see, not an outage."""
    polar_client.checkouts.create.side_effect = PolarClientError(422, None)
    with pytest.raises(PolarClientError):
        await polar_provider.create_checkout("product", bob_member_user)


def test_parse_user_id() -> None:
    """Test a customer created elsewhere, with another external id, is no user."""
    assert parse_user_id("not-a-uuid") is None


@pytest.mark.asyncio(loop_scope="function")
async def test_aclose(
    polar_provider: PolarPaymentProvider, polar_client: MockType
) -> None:
    """Test the HTTP client is closed."""
    await polar_provider.aclose()
    polar_client.__aexit__.assert_awaited_once()
