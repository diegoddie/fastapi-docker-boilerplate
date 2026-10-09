"""The users package schemas."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints, field_validator

from app.commons.schemas import BasePublicSchema, UTCAwareDatetime
from app.users.enums import Group
from app.users.models import BaseUser

Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]


class UserPublicSchemaCreate(BaseUser, BasePublicSchema):
    """The user public schema create (self-registration)."""

    password: Password


class UserPublicSchemaResponse(BaseUser, BasePublicSchema):
    """The user public schema response."""

    id: UUID
    groups: list[Group]
    is_active: bool
    datetime_created: datetime


def reject_null(value: object) -> object:
    """Reject an explicit null: omit the field instead to leave it unchanged."""
    if value is None:
        raise ValueError("Field cannot be null")
    return value


class UserMePublicSchemaUpdate(BasePublicSchema):
    """The user public schema update for the current user's own profile."""

    first_name: Name | None = None
    last_name: Name | None = None

    # Why: `None` here means "not sent" (PATCH semantics); these columns are not
    # nullable, so an explicit null is a client error, not a database error.
    _not_null = field_validator("first_name", "last_name", mode="before")(reject_null)


class UserPublicSchemaUpdate(UserMePublicSchemaUpdate):
    """The user public schema update for administrators."""

    groups: list[Group] | None = None
    datetime_disabled: UTCAwareDatetime | None = None

    _groups_not_null = field_validator("groups", mode="before")(reject_null)
