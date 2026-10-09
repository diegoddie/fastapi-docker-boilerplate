"""
The auth package security primitives: password hashing and access tokens.

Why: services depend on the ``PasswordHasher`` and ``AccessTokenCodec`` protocols,
not on argon2 or JWT, so implementations can be swapped (and faked in tests)
without touching the business logic.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Protocol
from uuid import UUID

import jwt
from fastapi import Depends
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings


class PasswordHasher(Protocol):
    """Hash and verify passwords."""

    def hash(self, password: str) -> str:
        """Return the hash of a password."""
        ...  # pragma: no cover

    def verify(self, password: str, password_hash: str) -> bool:
        """Tell if a password matches a hash."""
        ...  # pragma: no cover


class Argon2PasswordHasher:
    """Password hasher based on argon2id, the OWASP recommended algorithm."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self._hasher = PasswordHash((Argon2Hasher(),))

    def hash(self, password: str) -> str:
        """Return the hash of a password."""
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """Tell if a password matches a hash."""
        return self._hasher.verify(password, password_hash)


@dataclass(frozen=True)
class AccessToken:
    """A signed access token and its lifetime in seconds."""

    token: str
    expires_in: int


class InvalidAccessTokenError(Exception):
    """The access token is malformed, tampered with or expired."""


class AccessTokenCodec(Protocol):
    """Issue and read access tokens."""

    def encode(self, user_id: UUID) -> AccessToken:
        """Return an access token for a user."""
        ...  # pragma: no cover

    def decode(self, token: str) -> UUID:
        """Return the user id of a valid access token."""
        ...  # pragma: no cover


class JWTAccessTokenCodec:
    """Access tokens as short-lived signed JWTs carrying only the user id."""

    def __init__(self, secret_key: str, algorithm: str, lifetime: timedelta) -> None:
        """Initialize the instance."""
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.lifetime = lifetime

    def encode(self, user_id: UUID) -> AccessToken:
        """Return an access token for a user."""
        now = datetime.now(UTC)
        payload = {"sub": str(user_id), "iat": now, "exp": now + self.lifetime}
        return AccessToken(
            token=jwt.encode(payload, self.secret_key, algorithm=self.algorithm),
            expires_in=int(self.lifetime.total_seconds()),
        )

    def decode(self, token: str) -> UUID:
        """Return the user id of a valid access token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["exp", "iat", "sub"]},
            )
            return UUID(payload["sub"])
        except (jwt.InvalidTokenError, ValueError) as e:
            raise InvalidAccessTokenError from e


password_hasher = Argon2PasswordHasher()


def get_password_hasher() -> PasswordHasher:
    """Return the password hasher."""
    return password_hasher


def get_access_token_codec() -> AccessTokenCodec:
    """Return the access token codec configured from the settings."""
    return JWTAccessTokenCodec(
        secret_key=settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
        lifetime=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
AccessTokenCodecDep = Annotated[AccessTokenCodec, Depends(get_access_token_codec)]
