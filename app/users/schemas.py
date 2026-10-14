"""The users package schemas."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints, field_validator

from app.commons.schemas import BasePublicSchema, UTCAwareDatetime, reject_null
from app.users.constants import NAME_MAX_LENGTH
from app.users.enums import Group
from app.users.models import BaseUser

Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
FirstName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH),
]
LastName = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=NAME_MAX_LENGTH)
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


class UserMePublicSchemaUpdate(BasePublicSchema):
    """The user public schema update for the current user's own profile."""

    first_name: FirstName | None = None
    last_name: LastName | None = None

    _not_null = field_validator("first_name", "last_name", mode="before")(reject_null)


class UserPublicSchemaUpdate(UserMePublicSchemaUpdate):
    """The user public schema update for administrators."""

    groups: list[Group] | None = None
    datetime_disabled: UTCAwareDatetime | None = None

    _groups_not_null = field_validator("groups", mode="before")(reject_null)
