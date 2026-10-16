"""
The auth package external identity providers (e.g. Google).

Why: the sign-in flow depends on the ``IdentityProvider`` protocol, so adding
another provider (GitHub, Apple...) means adding a class, not changing the flow.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import Annotated, Any, Protocol

import jwt
from fastapi import Depends
from starlette.concurrency import run_in_threadpool

from app.auth.constants import GMAIL_DOMAIN, GOOGLE_ISSUERS, GOOGLE_PROVIDER
from app.core.config import settings
from app.core.exceptions import NotFoundHTTPException
from app.users.constants import NAME_MAX_LENGTH


@dataclass(frozen=True)
class ExternalIdentityClaims:
    """The identity asserted by an external provider."""

    provider: str
    subject: str
    email: str
    email_verified: bool
    first_name: str
    last_name: str
    # Why: a provider may report an address as verified long after its owner
    # lost it; only for its own addresses is it authoritative (e.g. Gmail).
    email_authoritative: bool = False


class InvalidIdentityTokenError(Exception):
    """The identity token is malformed, forged, expired or not meant for us."""


class IdentityProviderUnavailableError(Exception):
    """The identity provider could not be reached to verify a token."""


class IdentityProvider(Protocol):
    """Verify the identity tokens issued by an external provider."""

    async def verify(self, token: str) -> ExternalIdentityClaims:
        """Return the identity asserted by a valid token."""
        ...  # pragma: no cover


SigningKeyResolver = Callable[[str], Any]


class GoogleIdentityProvider:
    """Verify Google ID tokens, as issued by "Sign in with Google" on the frontend."""

    def __init__(
        self, client_id: str, signing_key_resolver: SigningKeyResolver
    ) -> None:
        """Initialize the instance."""
        self.client_id = client_id
        self.signing_key_resolver = signing_key_resolver

    async def verify(self, token: str) -> ExternalIdentityClaims:
        """Return the identity asserted by a valid Google ID token."""
        try:
            # Why: fetching Google's public keys is blocking I/O (cached afterwards),
            # so it runs in a thread instead of blocking the event loop.
            signing_key = await run_in_threadpool(self.signing_key_resolver, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=GOOGLE_ISSUERS,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "email"]},
            )
        except jwt.PyJWKClientConnectionError as e:
            raise IdentityProviderUnavailableError from e
        except jwt.PyJWTError as e:
            raise InvalidIdentityTokenError from e
        email = str(claims["email"])
        email_verified = claims.get("email_verified") is True
        domain = email.rpartition("@")[2].lower()
        hosted_domain = claims.get("hd")
        first_name = (
            claims.get("given_name") or claims.get("name") or email.split("@")[0]
        )
        return ExternalIdentityClaims(
            provider=GOOGLE_PROVIDER,
            subject=str(claims["sub"]),
            email=email,
            email_verified=email_verified,
            first_name=str(first_name)[:NAME_MAX_LENGTH],
            last_name=str(claims.get("family_name", ""))[:NAME_MAX_LENGTH],
            # Why: Google is authoritative for Gmail addresses and for the domain
            # of a Workspace account (the ``hd`` claim), not for other addresses.
            email_authoritative=email_verified
            and (
                domain == GMAIL_DOMAIN
                or (isinstance(hosted_domain, str) and domain == hosted_domain.lower())
            ),
        )


@cache
def _google_identity_provider(client_id: str, certs_url: str) -> GoogleIdentityProvider:
    """Return one provider per configuration, so Google's keys are fetched once."""
    jwks_client = jwt.PyJWKClient(certs_url, cache_keys=True, lifespan=3600)
    return GoogleIdentityProvider(client_id, jwks_client.get_signing_key_from_jwt)


def get_google_identity_provider() -> IdentityProvider:
    """Return the Google identity provider, if Google sign-in is configured."""
    if not settings.GOOGLE_CLIENT_ID:
        raise NotFoundHTTPException(
            message="Google sign-in is not configured.",
            error_code="GOOGLE_SIGN_IN_DISABLED",
        )
    return _google_identity_provider(
        settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CERTS_URL
    )


GoogleIdentityProviderDep = Annotated[
    IdentityProvider, Depends(get_google_identity_provider)
]
