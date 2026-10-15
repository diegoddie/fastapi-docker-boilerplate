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
from anyio import CapacityLimiter, to_thread
from anyio.lowlevel import RunVar
from fastapi import Depends
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings


class PasswordHasher(Protocol):
    """
    Hash and verify passwords.

    Why: the methods are async because a good password hash is slow on purpose,
    so an implementation must not run it on the event loop.
    """

    async def hash(self, password: str) -> str:
        """Return the hash of a password."""
        ...  # pragma: no cover

    async def verify(self, password: str, password_hash: str) -> bool:
        """Tell if a password matches a hash."""
        ...  # pragma: no cover


class Argon2PasswordHasher:
    """
    Password hasher based on argon2id, the OWASP recommended algorithm.

    Why: argon2 takes ~150 ms of CPU and 64 MiB of memory per hash, on purpose.
    It runs in a worker thread, so the event loop keeps serving other requests
    (argon2 releases the GIL), and at most ``concurrency`` hashes run at once in
    a process: the others wait their turn instead of taking 64 MiB each, which
    could exhaust the memory of the container.
    """

    def __init__(self, concurrency: int) -> None:
        """Initialize the instance."""
        self._hasher = PasswordHash((Argon2Hasher(),))
        self._concurrency = concurrency
        # Why: a limiter belongs to an event loop, so there is one per loop, as
        # for Starlette's own thread limiter.
        self._limiter: RunVar[CapacityLimiter] = RunVar("password_hash_limiter")

    async def hash(self, password: str) -> str:
        """Return the hash of a password."""
        return await to_thread.run_sync(
            self._hasher.hash, password, limiter=self._get_limiter()
        )

    async def verify(self, password: str, password_hash: str) -> bool:
        """Tell if a password matches a hash."""
        return await to_thread.run_sync(
            self._hasher.verify, password, password_hash, limiter=self._get_limiter()
        )

    def _get_limiter(self) -> CapacityLimiter:
        """Return the limiter of the running event loop."""
        try:
            return self._limiter.get()
        except LookupError:
            limiter = CapacityLimiter(self._concurrency)
            self._limiter.set(limiter)
            return limiter


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


password_hasher = Argon2PasswordHasher(settings.PASSWORD_HASH_CONCURRENCY)


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
