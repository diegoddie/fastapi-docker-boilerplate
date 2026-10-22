"""The ai package dependencies."""

from datetime import timedelta
from functools import cache
from typing import Annotated

from fastapi import Depends
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from app.ai.constants import (
    AI_REQUESTS_RATE_LIMIT,
    EFFORT,
    FALLBACK_BETA,
    MAX_TOKENS,
)
from app.auth.dependencies import AuthenticatedUser
from app.core.config import settings
from app.core.exceptions import NotFoundHTTPException
from app.ratelimit.dependencies import RateLimiterDep
from app.ratelimit.services import RateLimit


@cache
def build_chat_model() -> BaseChatModel | None:
    """Return the chat model, created once; None when no API key is set."""
    if settings.ANTHROPIC_API_KEY is None:
        return None
    # Why: the current models reject temperature, top_p, top_k and a forced tool
    # choice, so none is set; thinking is adaptive and the effort explicit.
    return ChatAnthropic(
        model=settings.AI_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=MAX_TOKENS,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=settings.AI_MAX_RETRIES,
        thinking={"type": "adaptive"},
        effort=EFFORT,
        betas=[FALLBACK_BETA],
        model_kwargs={"fallbacks": "default"},
    )


def get_chat_model() -> BaseChatModel:
    """Return the chat model, or answer 404 when AI is not configured."""
    chat_model = build_chat_model()
    if chat_model is None:
        raise NotFoundHTTPException(
            message="AI features are not enabled", error_code="AI_DISABLED"
        )
    return chat_model


async def limit_ai_requests(user: AuthenticatedUser, limiter: RateLimiterDep) -> None:
    """Limit the AI requests of each user."""
    await limiter.hit(
        RateLimit(
            AI_REQUESTS_RATE_LIMIT,
            settings.RATE_LIMIT_AI_REQUESTS_PER_HOUR,
            timedelta(hours=1),
        ),
        str(user.id),
    )


ChatModelDep = Annotated[BaseChatModel, Depends(get_chat_model)]
