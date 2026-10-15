"""The todos package router."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page

from app.auth.dependencies import AuthenticatedUser, require_any_permissions
from app.commons.exports import csv_response
from app.commons.pagination import paginate
from app.core.database import AsyncDBSession
from app.todos.constants import (
    CAN_CREATE_TODO,
    CAN_DELETE_TODO,
    CAN_EDIT_TODO,
    CAN_VIEW_TODO,
)
from app.todos.schemas import (
    TodoCSVSchema,
    TodoFilter,
    TodoPublicSchemaCreate,
    TodoPublicSchemaResponse,
    TodoPublicSchemaUpdate,
)
from app.todos.services import TodoService

router = APIRouter()


@router.post(
    "/todo/",
    summary="Create a todo",
    status_code=status.HTTP_201_CREATED,
    response_model=TodoPublicSchemaResponse,
    dependencies=[Depends(require_any_permissions([CAN_CREATE_TODO]))],
)
async def create_todo_route(
    payload: TodoPublicSchemaCreate, session: AsyncDBSession, user: AuthenticatedUser
) -> Any:
    """Create todo route."""
    return await TodoService.create(payload, session, user)


@router.get(
    "/todo/",
    summary="Get a list of todos",
    status_code=status.HTTP_200_OK,
    response_model=Page[TodoPublicSchemaResponse],
    dependencies=[Depends(require_any_permissions([CAN_VIEW_TODO]))],
)
async def list_todos_route(
    filters: Annotated[TodoFilter, Query()],
    session: AsyncDBSession,
    user: AuthenticatedUser,
) -> Any:
    """List todos route."""
    return await paginate(session, TodoService.list_query(filters, user))


@router.get(
    "/todo/download/",
    summary="Download the todos as CSV",
    status_code=status.HTTP_200_OK,
    response_class=StreamingResponse,
    responses={status.HTTP_200_OK: {"content": {"text/csv": {}}}},
    dependencies=[Depends(require_any_permissions([CAN_VIEW_TODO]))],
)
async def download_todos_route(
    filters: Annotated[TodoFilter, Query()],
    session: AsyncDBSession,
    user: AuthenticatedUser,
) -> StreamingResponse:
    """Download todos route: the same filters as the list, without pagination."""
    return csv_response(
        session, TodoService.list_query(filters, user), TodoCSVSchema, "todos.csv"
    )


@router.get(
    "/todo/{todo_id:uuid}/",
    summary="Get a todo detail",
    status_code=status.HTTP_200_OK,
    response_model=TodoPublicSchemaResponse,
    dependencies=[Depends(require_any_permissions([CAN_VIEW_TODO]))],
)
async def detail_todo_route(
    todo_id: UUID, session: AsyncDBSession, user: AuthenticatedUser
) -> Any:
    """Detail todo route."""
    return await TodoService.get_by_id(todo_id, session, user)


@router.patch(
    "/todo/{todo_id:uuid}/",
    summary="Update a todo",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_any_permissions([CAN_EDIT_TODO]))],
)
async def update_todo_route(
    todo_id: UUID,
    payload: TodoPublicSchemaUpdate,
    session: AsyncDBSession,
    user: AuthenticatedUser,
) -> None:
    """Update todo route."""
    await TodoService.update(todo_id, payload, session, user)


@router.delete(
    "/todo/{todo_id:uuid}/",
    summary="Delete a todo",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_any_permissions([CAN_DELETE_TODO]))],
)
async def delete_todo_route(
    todo_id: UUID, session: AsyncDBSession, user: AuthenticatedUser
) -> None:
    """Delete todo route."""
    await TodoService.delete(todo_id, session, user)
