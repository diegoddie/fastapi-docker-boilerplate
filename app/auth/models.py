"""The auth package models."""

from datetime import datetime
from uuid import UUID, uuid7

from sqlmodel import Field, Relationship

from app.commons.models import DatetimeCreatedMixin
from app.commons.types import UTCDateTime
from app.users.models import User


class RefreshToken(DatetimeCreatedMixin, table=True):
    """
    A refresh token, stored as a SHA-256 hash (the plain token is never saved).

    Tokens issued from the same login share a ``family_id``: every refresh revokes
    the presented token and issues a new one in the same family (rotation).
    """

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
    user: User = Relationship()
    family_id: UUID = Field(index=True)
    token_hash: str = Field(max_length=64, unique=True)
    datetime_expires: datetime = Field(sa_type=UTCDateTime)
    datetime_revoked: datetime | None = Field(default=None, sa_type=UTCDateTime)
