"""The todos package services."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from app.analytics.constants import TODO_CREATED  # copier:posthog
from app.analytics.services import Analytics  # copier:posthog
from app.core.exceptions import NotFoundHTTPException
from app.todos.constants import CAN_MANAGE_ALL_TODOS
from app.todos.models import Todo
from app.todos.schemas import (
    TodoFilter,
    TodoPublicSchemaCreate,
    TodoPublicSchemaUpdate,
)
from app.users.models import User


class TodoService:
    """The todo service."""

    @staticmethod
    def get_where_clause(user: User) -> list[ColumnElement[bool]]:
        """Return the conditions limiting the todos a user can reach."""
        # Why: a todo of someone else is "not found", not "forbidden", so the
        # API never reveals that it exists.
        clause: list[ColumnElement[bool]] = [col(Todo.datetime_disabled).is_(None)]
        if CAN_MANAGE_ALL_TODOS not in user.permissions:
            clause.append(col(Todo.owner_id) == user.id)
        return clause

    @staticmethod
    async def get_by_id(todo_id: UUID, session: AsyncSession, user: User) -> Todo:
        """Return a todo the user can reach."""
        todo = (
            await session.exec(
                select(Todo).where(
                    col(Todo.id) == todo_id, *TodoService.get_where_clause(user)
                )
            )
        ).one_or_none()
        if todo is None:
            raise NotFoundHTTPException(
                message=f"Todo with id {todo_id} not found",
                error_code="TODO_NOT_FOUND",
            )
        return todo

    @staticmethod
    def list_query(filters: TodoFilter, user: User) -> SelectOfScalar[Todo]:
        """Return the query of the todos a user can reach, filtered and ordered."""
        query = select(Todo).where(*TodoService.get_where_clause(user))
        # Why: the id goes last, as a tie-breaker that keeps pages stable.
        return filters.apply(query).order_by(col(Todo.id))

    @staticmethod
    async def create(
        payload: TodoPublicSchemaCreate,
        session: AsyncSession,
        user: User,
        analytics: Analytics,  # copier:posthog
    ) -> Todo:
        """Create a todo owned by the user."""
        todo = Todo.model_validate(payload.model_dump() | {"owner_id": user.id})
        session.add(todo)
        await session.commit()
        # copier:posthog:start
        # Why: what the product needs to know, never the text the user wrote.
        analytics.capture(
            TODO_CREATED,
            user.id,
            {"priority": todo.priority, "has_due_date": todo.due_date is not None},
        )
        # copier:posthog:end
        return todo

    @staticmethod
    async def update(
        todo_id: UUID,
        payload: TodoPublicSchemaUpdate,
        session: AsyncSession,
        user: User,
    ) -> None:
        """Update the fields sent of a todo."""
        todo = await TodoService.get_by_id(todo_id, session, user)
        todo.sqlmodel_update(payload.model_dump(exclude_unset=True))
        session.add(todo)
        await session.commit()

    @staticmethod
    async def delete(todo_id: UUID, session: AsyncSession, user: User) -> None:
        """Delete a todo (soft delete: it is kept, but hidden from the API)."""
        todo = await TodoService.get_by_id(todo_id, session, user)
        todo.datetime_disabled = datetime.now(UTC)
        session.add(todo)
        await session.commit()
