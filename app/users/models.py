"""The users package models."""

from datetime import datetime
from uuid import UUID, uuid7

from pydantic import EmailStr, computed_field, field_validator
from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import MutableList
from sqlmodel import Field, SQLModel

from app.commons.models import BaseSQLModel
from app.commons.types import UTCDateTime
from app.users.constants import EMAIL_MAX_LENGTH, GROUPS, NAME_MAX_LENGTH
from app.users.enums import Group


class BaseUser(SQLModel):
    """The base user: fields shared by the table model and the API schemas."""

    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH, unique=True)
    first_name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    # Why: optional, because some people (and some external accounts) have one name.
    last_name: str = Field(default="", max_length=NAME_MAX_LENGTH)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Store emails in lowercase, so uniqueness is case-insensitive."""
        return value.lower()


class User(BaseUser, BaseSQLModel, table=True):
    """A user."""

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    # Why: nullable, because users signing in with an external identity provider
    # may have no password at all.
    password_hash: str | None = Field(default=None, max_length=255)
    groups: list[str] = Field(
        default_factory=lambda: [Group.MEMBER],
        sa_column=Column(
            MutableList.as_mutable(ARRAY(String(32))),
            nullable=False,
            server_default=text("'{}'"),
        ),
    )

    # Why: set when the user proved they own the address: they opened a link
    # sent to it, or signed in with a provider authoritative for it (Gmail).
    datetime_email_verified: datetime | None = Field(default=None, sa_type=UTCDateTime)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_email_verified(self) -> bool:
        """Tell if the user proved they own their email address."""
        return self.datetime_email_verified is not None

    @property
    def permissions(self) -> frozenset[str]:
        """Return the permissions granted by the user's groups."""
        return frozenset().union(*(GROUPS[Group(group)] for group in self.groups))
