"""
The ai fixtures.

No test ever calls Anthropic or Langfuse:

- ``no_ai_services`` (automatic) clears their keys, so the real chat model and
  the Langfuse client are never built;
- ``fake_chat_model`` replaces the chat model with ``FakeChatModel``, which
  answers what the test prepares, parsed the way ``ChatAnthropic`` parses a
  structured output, and records the prompts and whether a database
  transaction was open meanwhile;
- ``langfuse_spans`` turns tracing on, with the spans kept in memory.
"""

import json
from collections.abc import Iterator
from functools import partial
from operator import itemgetter
from typing import Any
from uuid import uuid4

import anthropic
import httpx2
import pytest
from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableMap, RunnablePassthrough
from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ai.dependencies import build_chat_model, get_chat_model
from app.ai.tracing import get_langfuse
from app.core.config import settings


class FakeChatModel(BaseChatModel):
    """A chat model that answers with prepared messages, or fails."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session: AsyncSession
    answers: list[AIMessage | Exception] = Field(default_factory=list)
    prompts: list[list[BaseMessage]] = Field(default_factory=list)
    in_transaction: list[bool] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        """Return the type of the model."""
        return "fake"

    def answer(
        self,
        content: dict[str, Any] | str,
        stop_reason: str = "end_turn",
        refusal_category: str | None = None,
    ) -> None:
        """Prepare the next answer, shaped like Claude's."""
        stop_details = refusal_category and {
            "type": "refusal",
            "category": refusal_category,
        }
        self.answers.append(
            AIMessage(
                content=content if isinstance(content, str) else json.dumps(content),
                response_metadata={
                    "model_name": "claude-opus-5-5",
                    "stop_reason": stop_reason,
                    "stop_details": stop_details,
                },
                usage_metadata={
                    "input_tokens": 120,
                    "output_tokens": 340,
                    "total_tokens": 460,
                },
            )
        )

    def fail(self, status_code: int | None = None) -> None:
        """Prepare the next call to fail with a status, or with a timeout."""
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        self.answers.append(
            anthropic.APITimeoutError(request=request)
            if status_code is None
            else anthropic.APIStatusError(
                "error",
                response=httpx2.Response(status_code, request=request),
                body=None,
            )
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Return the next prepared answer, recording the prompt."""
        self.prompts.append(messages)
        self.in_transaction.append(self.session.in_transaction())
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return ChatResult(generations=[ChatGeneration(message=answer)])

    def with_structured_output(
        self,
        schema: dict[str, Any] | type,
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, dict[str, Any] | BaseModel]:
        """Parse the answer the way ``ChatAnthropic`` does with ``json_schema``."""
        assert isinstance(schema, type)
        assert include_raw
        assert kwargs == {"method": "json_schema"}
        parse = RunnablePassthrough.assign(
            parsed=itemgetter("raw") | PydanticOutputParser(pydantic_object=schema),
            parsing_error=lambda _: None,
        )
        unparsed = RunnablePassthrough.assign(parsed=lambda _: None)
        return RunnableMap(raw=self) | parse.with_fallbacks(
            [unparsed], exception_key="parsing_error"
        )


@pytest.fixture(autouse=True)
def no_ai_services(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear the keys of Anthropic and Langfuse, so no test ever calls them."""
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", None)
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", None)
    build_chat_model.cache_clear()
    get_langfuse.cache_clear()
    yield
    build_chat_model.cache_clear()
    get_langfuse.cache_clear()


@pytest.fixture
def fake_chat_model(test_app: FastAPI, async_db_session: AsyncSession) -> FakeChatModel:
    """Replace the chat model with a fake that answers what the test prepares."""
    fake = FakeChatModel(session=async_db_session)
    test_app.dependency_overrides[get_chat_model] = lambda: fake
    return fake


@pytest.fixture
def langfuse_spans(monkeypatch: pytest.MonkeyPatch) -> Iterator[InMemorySpanExporter]:
    """Turn tracing on, keeping the spans in memory instead of sending them."""
    exporter = InMemorySpanExporter()
    # Why: Langfuse keeps one client per public key for the whole process.
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", f"pk-lf-{uuid4()}")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", SecretStr("sk-lf-test"))
    monkeypatch.setattr(
        "app.ai.tracing.Langfuse", partial(Langfuse, span_exporter=exporter)
    )
    yield exporter
    client = get_langfuse()
    assert client is not None
    client.shutdown()
