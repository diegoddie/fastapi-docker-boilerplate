"""
The auth fixtures.

No test ever calls Google:

- ``google_identity_provider`` replaces Google with a fake that asserts the
  identity of Erin, a Google user who has no account here yet;
- ``google_id_token`` signs ID tokens the way Google does, with a key generated
  for the test session, to test the real ``GoogleIdentityProvider``;
- ``recording_password_hasher`` hashes for real, and records whether a database
  transaction was open meanwhile.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.identity import (
    ExternalIdentityClaims,
    GoogleIdentityProvider,
    get_google_identity_provider,
)
from app.auth.security import (
    JWTAccessTokenCodec,
    get_password_hasher,
    password_hasher,
)
from tests.factories.auth import RefreshTokenFactory


class FakeIdentityProvider:
    """An identity provider that asserts a fixed identity, or fails."""

    def __init__(self, claims: ExternalIdentityClaims) -> None:
        """Initialize the instance."""
        self.claims = claims
        self.error: Exception | None = None

    async def verify(self, token: str) -> ExternalIdentityClaims:
        """Return the fixed identity, or raise the error."""
        if self.error is not None:
            raise self.error
        return self.claims


class RecordingPasswordHasher:
    """The real password hasher, recording whether a transaction was open."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the instance."""
        self.session = session
        self.in_transaction: list[bool] = []

    async def hash(self, password: str) -> str:
        """Return the hash of a password."""
        self.in_transaction.append(self.session.in_transaction())
        return await password_hasher.hash(password)

    async def verify(self, password: str, password_hash: str) -> bool:
        """Tell if a password matches a hash."""
        self.in_transaction.append(self.session.in_transaction())
        return await password_hasher.verify(password, password_hash)


@dataclass(frozen=True)
class FakeSigningKey:
    """A signing key, shaped like the ones returned by PyJWKClient."""

    key: Any


@pytest.fixture
def erin_google_identity() -> ExternalIdentityClaims:
    """Return the Google identity of Erin, who has no account here yet."""
    return ExternalIdentityClaims(
        provider="google",
        subject="google-subject-erin",
        email="Erin.Example@gmail.com",
        email_verified=True,
        first_name="Erin",
        last_name="Example",
    )


@pytest.fixture
def google_identity_provider(
    test_app: FastAPI, erin_google_identity: ExternalIdentityClaims
) -> FakeIdentityProvider:
    """Replace Google with a fake provider asserting Erin's identity."""
    provider = FakeIdentityProvider(erin_google_identity)
    test_app.dependency_overrides[get_google_identity_provider] = lambda: provider
    return provider


@pytest.fixture
def google_client_id() -> str:
    """Return the OAuth client id the test ID tokens are issued for."""
    return "test-client.apps.googleusercontent.com"


@pytest.fixture(scope="session")
def google_private_key() -> rsa.RSAPrivateKey:
    """Return the key the test ID tokens are signed with (slow: one per session)."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def google_id_token(
    google_private_key: rsa.RSAPrivateKey, google_client_id: str
) -> Callable[..., str]:
    """Return a function signing Google-like ID tokens (None drops a claim)."""

    def sign(key: rsa.RSAPrivateKey | None = None, **claims: Any) -> str:
        """Return a signed ID token with Erin's claims, changed by ``claims``."""
        now = datetime.now(UTC)
        payload = {
            "iss": "https://accounts.google.com",
            "aud": google_client_id,
            "sub": "google-subject-erin",
            "email": "Erin.Example@gmail.com",
            "email_verified": True,
            "given_name": "Erin",
            "family_name": "Example",
            "name": "Erin Example",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        } | claims
        return jwt.encode(
            {name: value for name, value in payload.items() if value is not None},
            key or google_private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    return sign


@pytest.fixture
def google_provider(
    google_client_id: str, google_private_key: rsa.RSAPrivateKey
) -> GoogleIdentityProvider:
    """Return the real Google provider, trusting the test key instead of Google's."""
    public_key = google_private_key.public_key()
    return GoogleIdentityProvider(
        google_client_id, lambda token: FakeSigningKey(public_key)
    )


@pytest.fixture
def jwt_access_token_codec() -> JWTAccessTokenCodec:
    """Return an access token codec with a test secret key and a 15 minute life."""
    return JWTAccessTokenCodec(
        secret_key="a-test-secret-key-that-is-long-enough-for-hs256",
        algorithm="HS256",
        lifetime=timedelta(minutes=15),
    )


@pytest.fixture
def refresh_token_factory(seed_factories: None) -> type[RefreshTokenFactory]:
    """Return the refresh token factory, bound to the test database."""
    return RefreshTokenFactory


@pytest.fixture
def recording_password_hasher(
    test_app: FastAPI, async_db_session: AsyncSession
) -> RecordingPasswordHasher:
    """Replace the password hasher with one recording the open transactions."""
    hasher = RecordingPasswordHasher(async_db_session)
    test_app.dependency_overrides[get_password_hasher] = lambda: hasher
    return hasher
