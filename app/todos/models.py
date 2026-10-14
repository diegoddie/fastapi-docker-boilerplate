"""The todos package models."""

from datetime import date
from uuid import UUID, uuid7

from pydantic import field_validator
from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from app.commons.models import BaseSQLModel
from app.commons.types import pg_enum
from app.todos.constants import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH
from app.todos.enums import TodoPriority, TodoStatus


class BaseTodo(SQLModel):
    """The base todo: fields shared by the table model and the API schemas."""

    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    description: str = Field(default="", max_length=DESCRIPTION_MAX_LENGTH)
    status: TodoStatus = Field(
        default=TodoStatus.TODO,
        sa_column=Column(pg_enum(TodoStatus), nullable=False),
    )
    priority: TodoPriority = Field(
        default=TodoPriority.MEDIUM,
        sa_column=Column(pg_enum(TodoPriority), nullable=False),
    )
    due_date: date | None = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        """Strip the title, so a blank one is rejected as empty."""
        return value.strip() if isinstance(value, str) else value


class Todo(BaseTodo, BaseSQLModel, table=True):
    """A todo, owned by the user who created it."""

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
