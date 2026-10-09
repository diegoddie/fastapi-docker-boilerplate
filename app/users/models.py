"""The users package models."""

from uuid import UUID, uuid7

from pydantic import EmailStr, field_validator
from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import MutableList
from sqlmodel import Field, SQLModel

from app.commons.models import BaseSQLModel
from app.users.constants import GROUPS
from app.users.enums import Group


class BaseUser(SQLModel):
    """The base user: fields shared by the table model and the API schemas."""

    email: EmailStr = Field(max_length=320, unique=True)
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)

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

    @property
    def permissions(self) -> frozenset[str]:
        """Return the permissions granted by the user's groups."""
        return frozenset().union(*(GROUPS[Group(group)] for group in self.groups))
