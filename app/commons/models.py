"""The commons package models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import computed_field
from sqlmodel import Field, SQLModel

from app.commons.types import UTCDateTime

# Why: constraint and index names must be deterministic and identical whether the
# schema is built by the Alembic migrations or by `create_all` in the tests, so the
# convention is set here, in the module every table model depends on.
SQLModel.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class DatetimeCreatedMixin(SQLModel):
    """Creation timestamp, for append-only tables that don't need BaseSQLModel."""

    datetime_created: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=UTCDateTime
    )


class BaseSQLModel(DatetimeCreatedMixin):
    """Base table model: timestamps and soft delete. Subclasses define ``id``."""

    if TYPE_CHECKING:  # pragma: no cover
        id: UUID

    datetime_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=UTCDateTime,
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    datetime_disabled: datetime | None = Field(default=None, sa_type=UTCDateTime)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_active(self) -> bool:
        """Tell if the record has not been disabled (soft deleted)."""
        return self.datetime_disabled is None
