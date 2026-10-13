"""The auth package identity providers tests."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import status

from app.auth.identity import (
    ExternalIdentityClaims,
    GoogleIdentityProvider,
    IdentityProviderUnavailableError,
    InvalidIdentityTokenError,
    get_google_identity_provider,
)
from app.core.config import settings
from app.core.exceptions import NotFoundHTTPException


@pytest.mark.asyncio(loop_scope="function")
async def test_google_identity_provider_verify(
    google_provider: GoogleIdentityProvider,
    google_id_token: Callable[..., str],
    erin_google_identity: ExternalIdentityClaims,
) -> None:
    """Test a valid Google ID token gives the identity it asserts."""
    assert await google_provider.verify(google_id_token()) == erin_google_identity


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("claims", "first_name", "last_name"),
    [
        ({"given_name": None, "family_name": None}, "Erin Example", ""),
        ({"given_name": None, "family_name": None, "name": None}, "Erin.Example", ""),
        ({"given_name": "E" * 200}, "E" * 150, "Example"),
    ],
    ids=["full_name_only", "no_names", "long_name"],
)
async def test_google_identity_provider_verify_names(
    google_provider: GoogleIdentityProvider,
    google_id_token: Callable[..., str],
    claims: dict[str, Any],
    first_name: str,
    last_name: str,
) -> None:
    """Test the names fall back to the full name, then to the email, and fit."""
    identity = await google_provider.verify(google_id_token(**claims))
    assert (identity.first_name, identity.last_name) == (first_name, last_name)


@pytest.mark.asyncio(loop_scope="function")
async def test_google_identity_provider_verify_unverified_email(
    google_provider: GoogleIdentityProvider, google_id_token: Callable[..., str]
) -> None:
    """Test an unverified email is reported, not trusted."""
    identity = await google_provider.verify(google_id_token(email_verified=False))
    assert identity.email_verified is False


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "another-client.apps.googleusercontent.com"},
        {"iss": "https://accounts.evil.example"},
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"email": None},
    ],
    ids=["wrong_audience", "wrong_issuer", "expired", "no_email"],
)
async def test_google_identity_provider_verify_invalid(
    google_provider: GoogleIdentityProvider,
    google_id_token: Callable[..., str],
    claims: dict[str, Any],
) -> None:
    """Test tokens that are not Google's tokens for this client are rejected."""
    with pytest.raises(InvalidIdentityTokenError):
        await google_provider.verify(google_id_token(**claims))


@pytest.mark.asyncio(loop_scope="function")
async def test_google_identity_provider_verify_forged(
    google_provider: GoogleIdentityProvider, google_id_token: Callable[..., str]
) -> None:
    """Test a token signed with a key other than Google's is rejected."""
    forger_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(InvalidIdentityTokenError):
        await google_provider.verify(google_id_token(key=forger_key))


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("resolver_error", "expected_error"),
    [
        (jwt.DecodeError("Invalid token"), InvalidIdentityTokenError),
        (
            jwt.PyJWKClientConnectionError("Connection refused"),
            IdentityProviderUnavailableError,
        ),
    ],
    ids=["malformed_token", "google_unreachable"],
)
async def test_google_identity_provider_verify_key_errors(
    google_client_id: str,
    resolver_error: Exception,
    expected_error: type[Exception],
) -> None:
    """Test Google being unreachable is not mistaken for an invalid token."""

    def resolver(token: str) -> None:
        """Fail like PyJWKClient does."""
        raise resolver_error

    provider = GoogleIdentityProvider(google_client_id, resolver)
    with pytest.raises(expected_error):
        await provider.verify("token")


def test_get_google_identity_provider_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Google sign-in answers 404 until a client id is configured."""
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    with pytest.raises(NotFoundHTTPException) as error:
        get_google_identity_provider()
    assert error.value.status_code == status.HTTP_404_NOT_FOUND
    # Why: our exceptions put a dict in `detail`, typed as `str` by Starlette.
    assert cast(dict[str, str], error.value.detail) == {
        "message": "Google sign-in is not configured.",
        "errorCode": "GOOGLE_SIGN_IN_DISABLED",
    }


def test_get_google_identity_provider(
    monkeypatch: pytest.MonkeyPatch, google_client_id: str
) -> None:
    """Test the configured provider is created once and then reused."""
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", google_client_id)
    provider = get_google_identity_provider()
    assert isinstance(provider, GoogleIdentityProvider)
    assert provider.client_id == google_client_id
    assert get_google_identity_provider() is provider
