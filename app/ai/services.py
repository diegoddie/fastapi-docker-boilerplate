"""The ai package services."""

import time
from typing import Any, cast
from uuid import UUID

import anthropic
import structlog
from fastapi import status
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ai.prompts import SUBTASKS_SYSTEM_PROMPT, subtasks_prompt
from app.ai.schemas import SubtaskPlan
from app.core.exceptions import (
    BadGatewayHTTPException,
    ServiceUnavailableHTTPException,
    UnprocessableHTTPException,
)
from app.core.logs import get_request_id
from app.todos.services import TodoService
from app.users.models import User

logger = structlog.get_logger(__name__)


async def generate[T: BaseModel](
    chat_model: BaseChatModel,
    messages: list[BaseMessage],
    schema: type[T],
    *,
    name: str,
    user: User,
    callbacks: list[BaseCallbackHandler],
) -> T:
    """
    Return the model's answer in a schema, logging what it cost.

    Answer 503 when the model is unreachable, rate limited or overloaded, 422
    when it declines the request, and 502 when its answer does not fit the
    schema (e.g. cut off at the token limit).
    """
    structured = chat_model.with_structured_output(
        schema, method="json_schema", include_raw=True
    )
    started = time.perf_counter()
    try:
        result = cast(
            dict[str, Any],
            await structured.ainvoke(
                messages,
                config={
                    "run_name": name,
                    "callbacks": callbacks,
                    "metadata": {
                        "langfuse_user_id": str(user.id),
                        "request_id": get_request_id(),
                    },
                },
            ),
        )
    except anthropic.APIConnectionError as e:
        # Why: timeouts are connection errors too.
        logger.warning("ai_unavailable", name=name, error=type(e).__name__)
        raise _unavailable() from e
    except anthropic.APIStatusError as e:
        if (
            e.status_code != status.HTTP_429_TOO_MANY_REQUESTS
            and e.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR
        ):
            raise
        logger.warning("ai_unavailable", name=name, status_code=e.status_code)
        raise _unavailable() from e
    raw = cast(AIMessage, result["raw"])
    usage = raw.usage_metadata
    stop_reason = raw.response_metadata.get("stop_reason")
    # Why: never the prompt or the answer, which can hold personal data.
    logger.info(
        "ai_completion",
        name=name,
        model=raw.response_metadata.get("model_name"),
        stop_reason=stop_reason,
        refusal_category=(raw.response_metadata.get("stop_details") or {}).get(
            "category"
        ),
        input_tokens=usage["input_tokens"] if usage else None,
        output_tokens=usage["output_tokens"] if usage else None,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    if stop_reason == "refusal":
        raise UnprocessableHTTPException(
            message="The AI declined this request", error_code="AI_REFUSAL"
        )
    if result["parsed"] is None:
        raise BadGatewayHTTPException(
            message="The AI answered in an unexpected format",
            error_code="AI_INVALID_RESPONSE",
        )
    return cast(T, result["parsed"])


def _unavailable() -> ServiceUnavailableHTTPException:
    """Return the error for a model that cannot answer right now."""
    return ServiceUnavailableHTTPException(
        message="The AI service is unavailable, try again later",
        error_code="AI_UNAVAILABLE",
    )


class AIService:
    """The AI features."""

    @staticmethod
    async def suggest_todo_subtasks(
        todo_id: UUID,
        session: AsyncSession,
        user: User,
        chat_model: BaseChatModel,
        callbacks: list[BaseCallbackHandler],
    ) -> SubtaskPlan:
        """Return the subtasks the model suggests for a todo the user can reach."""
        todo = await TodoService.get_by_id(todo_id, session, user)
        # Why: the model takes seconds; meanwhile the connection is back in the pool.
        await session.commit()
        return await generate(
            chat_model,
            [
                SystemMessage(SUBTASKS_SYSTEM_PROMPT),
                HumanMessage(subtasks_prompt(todo)),
            ],
            SubtaskPlan,
            name="suggest_todo_subtasks",
            user=user,
            callbacks=callbacks,
        )
