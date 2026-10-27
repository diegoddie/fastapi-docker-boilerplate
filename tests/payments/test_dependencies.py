"""The payments package dependencies tests."""

import pytest
from pydantic import SecretStr
from pytest_mock import MockerFixture

from app.core.config import settings
from app.payments.dependencies import (
    build_payment_provider,
    close_payments,
    get_payment_provider,
)
from app.payments.polar_provider import PolarPaymentProvider


@pytest.mark.asyncio(loop_scope="function")
async def test_build_payment_provider(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    """Test Polar is used only with a token and a webhook secret, built once."""
    assert build_payment_provider() is None
    await close_payments()
    monkeypatch.setattr(settings, "POLAR_ACCESS_TOKEN", SecretStr("polar_oat_test"))
    monkeypatch.setattr(settings, "POLAR_WEBHOOK_SECRET", SecretStr("whsec_test"))
    monkeypatch.setattr(settings, "POLAR_PRODUCT_IDS", ["pro-monthly"])
    build_payment_provider.cache_clear()
    provider = get_payment_provider()
    assert isinstance(provider, PolarPaymentProvider)
    assert provider is build_payment_provider()
    assert (provider.webhook_secret, provider.product_ids) == (
        "whsec_test",
        frozenset({"pro-monthly"}),
    )
    aclose = mocker.patch.object(provider, "aclose")
    await close_payments()
    aclose.assert_awaited_once()
