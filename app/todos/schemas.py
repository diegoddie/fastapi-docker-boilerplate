"""The todos package schemas."""

from datetime import date, datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator
from sqlmodel import SQLModel

from app.commons.schemas import BaseCSVSchema, BasePublicSchema, reject_null
from app.filters import FilterBase
from app.todos.constants import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH
from app.todos.enums import TodoPriority, TodoStatus
from app.todos.models import BaseTodo, Todo

Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TITLE_MAX_LENGTH),
]
Description = Annotated[str, StringConstraints(max_length=DESCRIPTION_MAX_LENGTH)]


class TodoPublicSchemaCreate(BaseTodo, BasePublicSchema):
    """The todo public schema create."""


class TodoPublicSchemaUpdate(BasePublicSchema):
    """The todo public schema update: only the fields sent are changed."""

    title: Title | None = None
    description: Description | None = None
    status: TodoStatus | None = None
    priority: TodoPriority | None = None
    due_date: date | None = None

    _not_null = field_validator(
        "title", "description", "status", "priority", mode="before"
    )(reject_null)


class TodoPublicSchemaResponse(BaseTodo, BasePublicSchema):
    """The todo public schema response."""

    id: UUID
    owner_id: UUID
    datetime_created: datetime
    datetime_updated: datetime


class TodoCSVSchema(BaseCSVSchema):
    """A row of the todos CSV export."""

    title: str = Field(title="Title")
    description: str = Field(title="Description")
    status: TodoStatus = Field(title="Status")
    priority: TodoPriority = Field(title="Priority")
    due_date: date | None = Field(title="Due date")
    datetime_created: datetime = Field(title="Created at")


class TodoFilter(FilterBase):
    """The filters, search and ordering of the todos list."""

    model: ClassVar[type[SQLModel]] = Todo
    search_fields: ClassVar[tuple[str, ...]] = ("title", "description")
    sortable_fields: ClassVar[tuple[str, ...]] = (
        "title",
        "priority",
        "dueDate",
        "datetimeCreated",
    )
    default_order_by: ClassVar[str] = "-datetimeCreated"

    status: TodoStatus | None = None
    priority__in: list[TodoPriority] | None = None
    due_date__gte: date | None = None
    due_date__lte: date | None = None
    due_date__is_null: bool | None = None
