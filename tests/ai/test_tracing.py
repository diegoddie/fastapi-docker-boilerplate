"""The ai package tracing tests."""

import json

import pytest
from fastapi import status
from langfuse import LangfuseOtelSpanAttributes
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from app.ai.tracing import CONTENT_ATTRIBUTES, get_langfuse, get_tracing_callbacks
from app.core.config import settings
from app.todos.models import Todo
from app.users.models import User
from tests.pytest_plugins.ai import FakeChatModel
from tests.utils import AsyncClient


def test_tracing_disabled() -> None:
    """Test nothing is traced without the Langfuse keys."""
    assert get_langfuse() is None
    assert get_tracing_callbacks() == []


async def suggest_subtasks(
    async_client: AsyncClient,
    fake_chat_model: FakeChatModel,
    langfuse_spans: InMemorySpanExporter,
    todo: Todo,
) -> tuple[str, dict[str, ReadableSpan]]:
    """Ask for the subtasks of a todo; return the request id and the spans."""
    fake_chat_model.answer(
        {
            "subtasks": [
                {"title": "Collect", "description": "", "priority": "high"},
                {"title": "Write", "description": "", "priority": "low"},
            ]
        }
    )
    response = await async_client.post(
        f"/api/v1/todos/todo/{todo.id}/subtask-suggestions/"
    )
    assert response.status_code == status.HTTP_200_OK
    client = get_langfuse()
    assert client is not None
    client.flush()
    spans = {span.name: span for span in langfuse_spans.get_finished_spans()}
    return response.headers["X-Request-ID"], spans


@pytest.mark.asyncio(loop_scope="function")
async def test_tracing_without_content(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_report_todo: Todo,
    fake_chat_model: FakeChatModel,
    langfuse_spans: InMemorySpanExporter,
) -> None:
    """Test a call is traced with its user, request and tokens, but no text."""
    async_client.login(bob_member_user)
    request_id, spans = await suggest_subtasks(
        async_client, fake_chat_model, langfuse_spans, bob_report_todo
    )
    root = spans["suggest_todo_subtasks"].attributes or {}
    assert root[LangfuseOtelSpanAttributes.TRACE_USER_ID] == str(bob_member_user.id)
    assert json.loads(str(root["langfuse.trace.metadata.request_id"])) == request_id
    generation = spans["FakeChatModel"].attributes or {}
    assert json.loads(
        str(generation[LangfuseOtelSpanAttributes.OBSERVATION_USAGE_DETAILS])
    ) == {"input": 120, "output": 340, "total": 460}
    assert not [
        (span.name, name)
        for span in spans.values()
        for name in CONTENT_ATTRIBUTES
        if name in (span.attributes or {})
    ]


@pytest.mark.asyncio(loop_scope="function")
async def test_tracing_with_content(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    bob_member_user: User,
    bob_report_todo: Todo,
    fake_chat_model: FakeChatModel,
    langfuse_spans: InMemorySpanExporter,
) -> None:
    """Test the prompts and answers are traced when the settings allow it."""
    monkeypatch.setattr(settings, "LANGFUSE_CAPTURE_CONTENT", True)
    async_client.login(bob_member_user)
    _, spans = await suggest_subtasks(
        async_client, fake_chat_model, langfuse_spans, bob_report_todo
    )
    generation = spans["FakeChatModel"].attributes or {}
    assert "Write the quarterly report" in str(
        generation[LangfuseOtelSpanAttributes.OBSERVATION_INPUT]
    )
    assert "Collect" in str(generation[LangfuseOtelSpanAttributes.OBSERVATION_OUTPUT])
