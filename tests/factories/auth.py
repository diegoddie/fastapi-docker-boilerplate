"""The auth test factories."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.auth.models import RefreshToken
from tests.factories.base import BaseFactory


class RefreshTokenFactory(BaseFactory[RefreshToken]):
    """A refresh token factory, valid for 30 days (pass the user_id)."""

    __model__ = RefreshToken

    datetime_revoked = None

    @classmethod
    def family_id(cls) -> UUID:
        """Return a fake family id."""
        return UUID(cls.__faker__.uuid4())

    @classmethod
    def token_hash(cls) -> str:
        """Return a fake SHA-256 hash."""
        return str(cls.__faker__.sha256())

    @classmethod
    def datetime_expires(cls) -> datetime:
        """Return an expiry 30 days from now."""
        return datetime.now(UTC) + timedelta(days=30)
