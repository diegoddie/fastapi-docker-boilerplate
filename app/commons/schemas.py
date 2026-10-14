"""The commons package schemas."""

from datetime import UTC
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlmodel import SQLModel

UTCAwareDatetime = Annotated[
    AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))
]


class BasePublicSchema(SQLModel):
    """
    Base schema for request and response bodies: camelCase in JSON.

    Why: it extends SQLModel (not BaseModel) so that schemas can inherit the field
    definitions of the ``BaseXxx`` model classes.
    See https://github.com/fastapi/sqlmodel/discussions/855
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)  # type: ignore[assignment]


class BaseCSVSchema(BaseModel):
    """Base schema for the rows of a CSV export: the field titles are the headers."""

    model_config = ConfigDict(from_attributes=True)


def reject_null(value: object) -> object:
    """
    Reject an explicit null in a PATCH body: omit the field to leave it unchanged.

    Why: in update schemas ``None`` means "not sent", so an explicit null for a
    non-nullable column is a client error (422), not a database error.
    """
    if value is None:
        raise ValueError("Field cannot be null")
    return value
