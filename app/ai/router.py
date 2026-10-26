"""The ai package router."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.ai.constants import CAN_SUGGEST_TODO_SUBTASKS
from app.ai.dependencies import ChatModelDep, get_chat_model, limit_ai_requests
from app.ai.schemas import SubtaskSuggestionsPublicSchemaResponse
from app.ai.services import AIService
from app.ai.tracing import TracingCallbacksDep
from app.auth.dependencies import AuthenticatedUser, require_any_permissions
from app.core.database import AsyncDBSession

router = APIRouter()


@router.post(
    "/todo/{todo_id:uuid}/subtask-suggestions/",
    summary="Suggest the subtasks of a todo",
    status_code=status.HTTP_200_OK,
    response_model=SubtaskSuggestionsPublicSchemaResponse,
    # Why: in this order, a project without AI answers 404 before counting the
    # request against the user's limit.
    dependencies=[
        Depends(require_any_permissions([CAN_SUGGEST_TODO_SUBTASKS])),
        Depends(get_chat_model),
        Depends(limit_ai_requests),
    ],
)
async def suggest_todo_subtasks_route(
    todo_id: UUID,
    session: AsyncDBSession,
    user: AuthenticatedUser,
    chat_model: ChatModelDep,
    callbacks: TracingCallbacksDep,
) -> Any:
    """Suggest todo subtasks route."""
    return await AIService.suggest_todo_subtasks(
        todo_id, session, user, chat_model, callbacks
    )
