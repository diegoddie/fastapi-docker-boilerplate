"""The commons package schemas."""

from datetime import UTC
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, ConfigDict
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
