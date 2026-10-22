"""The ai package router tests."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from dirty_equals import IsDatetime, IsFloat, IsStr
from fastapi import status
from inline_snapshot import snapshot
from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ai.prompts import SUBTASKS_SYSTEM_PROMPT
from app.core.config import settings
from app.ratelimit.models import RateLimitCounter
from app.todos.models import Todo
from app.users.models import User
from tests.pytest_plugins.ai import FakeChatModel
from tests.utils import AsyncClient

DUMMY_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("method", "url"),
    [("post", f"/api/v1/todos/todo/{DUMMY_UUID}/subtask-suggestions/")],
    ids=["suggest_todo_subtasks"],
)
async def test_route_401(async_client: AsyncClient, method: str, url: str) -> None:
    """Test that every AI route requires authentication."""
    response = await getattr(async_client, method)(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("method", "url"),
    [("post", f"/api/v1/todos/todo/{DUMMY_UUID}/subtask-suggestions/")],
    ids=["suggest_todo_subtasks"],
)
async def test_route_403(
    async_client: AsyncClient, carol_viewer_user: User, method: str, url: str
) -> None:
    """Test that viewers cannot use the AI features."""
    async_client.login(carol_viewer_user)
    response = await getattr(async_client, method)(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["errorCode"] == "FORBIDDEN"


@pytest.mark.asyncio(loop_scope="function")
async def test_suggest_todo_subtasks_route_200(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_report_todo: Todo,
    fake_chat_model: FakeChatModel,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test the suggest todo subtasks route 200: the plan, ready to create."""
    fake_chat_model.answer(
        {
            "subtasks": [
                {
                    "title": "Collect the Q3 numbers",
                    "description": "Export sales and costs from the ERP.",
                    "priority": "high",
                },
                {
                    "title": "Draft the report",
                    "description": "Write the summary and the charts.",
                    "priority": "medium",
                },
            ]
        }
    )
    async_client.login(bob_member_user)
    response = await async_client.post(
        f"/api/v1/todos/todo/{bob_report_todo.id}/subtask-suggestions/"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == snapshot(
        {
            "subtasks": [
                {
                    "title": "Collect the Q3 numbers",
                    "description": "Export sales and costs from the ERP.",
                    "priority": "high",
                },
                {
                    "title": "Draft the report",
                    "description": "Write the summary and the charts.",
                    "priority": "medium",
                },
            ]
        }
    )
    ((system, human),) = fake_chat_model.prompts
    assert system == SystemMessage(SUBTASKS_SYSTEM_PROMPT)
    assert isinstance(human, HumanMessage)
    assert human.content == snapshot("""\
Split this todo into 2 to 8 subtasks, each with its priority.

<todo>
<title>Write the quarterly report</title>
<description>Numbers for Q3</description>
<priority>medium</priority>
<due_date>2026-10-15</due_date>
</todo>\
""")
    # The connection went back to the pool before the model was called.
    assert fake_chat_model.in_transaction == [False]
    assert log_events("ai_completion") == [
        {
            "event": "ai_completion",
            "name": "suggest_todo_subtasks",
            "model": "claude-opus-5-5",
            "stop_reason": "end_turn",
            "refusal_category": None,
            "input_tokens": 120,
            "output_tokens": 340,
            "duration_ms": IsFloat(ge=0),
            "request_id": IsStr(regex=r"[0-9a-f]{32}"),
            "user_id": str(bob_member_user.id),
            "logger": "app.ai.services",
            "level": "info",
            "timestamp": IsDatetime(iso_string=True),
        }
    ]


@pytest.mark.asyncio(loop_scope="function")
async def test_suggest_todo_subtasks_route_404_ai_disabled(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    bob_report_todo: Todo,
) -> None:
    """Test the suggest todo subtasks route 404 without an API key, uncounted."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        f"/api/v1/todos/todo/{bob_report_todo.id}/subtask-suggestions/"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "AI features are not enabled",
                "errorCode": "AI_DISABLED",
            }
        }
    )
    assert (await async_db_session.exec(select(RateLimitCounter))).all() == []


@pytest.mark.asyncio(loop_scope="function")
async def test_suggest_todo_subtasks_route_404_other_owner(
    async_client: AsyncClient,
    bob_member_user: User,
    alice_review_todo: Todo,
    fake_chat_model: FakeChatModel,
) -> None:
    """Test the suggest todo subtasks route 404 on someone else's todo."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        f"/api/v1/todos/todo/{alice_review_todo.id}/subtask-suggestions/"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"]["errorCode"] == "TODO_NOT_FOUND"
    assert fake_chat_model.prompts == []


@pytest.mark.asyncio(loop_scope="function")
async def test_suggest_todo_subtasks_route_422_refusal(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_report_todo: Todo,
    fake_chat_model: FakeChatModel,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test the suggest todo subtasks route 422 when the model declines."""
    fake_chat_model.answer("", stop_reason="refusal", refusal_category="cyber")
    async_client.login(bob_member_user)
    response = await async_client.post(
        f"/api/v1/todos/todo/{bob_report_todo.id}/subtask-suggestions/"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "The AI declined this request",
                "errorCode": "AI_REFUSAL",
            }
        }
    )
    (event,) = log_events("ai_completion")
    assert (event["stop_reason"], event["refusal_category"]) == ("refusal", "cyber")


@pytest.mark.asyncio(loop_scope="function")
async def test_suggest_todo_subtasks_route_429(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    bob_member_user: User,
    bob_report_todo: Todo,
    fake_chat_model: FakeChatModel,
    start_of_minute: datetime,
) -> None:
    """Test the AI requests of a user are limited per hour."""
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_REQUESTS_PER_HOUR", 1)
    fake_chat_model.answer(
        {
            "subtasks": [
                {"title": "Collect", "description": "", "priority": "high"},
                {"title": "Write", "description": "", "priority": "low"},
            ]
        }
    )
    async_client.login(bob_member_user)
    url = f"/api/v1/todos/todo/{bob_report_todo.id}/subtask-suggestions/"
    assert (await async_client.post(url)).status_code == status.HTTP_200_OK
    response = await async_client.post(url)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert len(fake_chat_model.prompts) == 1


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("content", "stop_reason"),
    [
        (
            {"subtasks": [{"title": "All", "description": "", "priority": "low"}]},
            "end_turn",
        ),
        ('{"subtasks": [{"title": "Coll', "max_tokens"),
    ],
    ids=["too_few_subtasks", "cut_off"],
)
async def test_suggest_todo_subtasks_route_502(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_report_todo: Todo,
    fake_chat_model: FakeChatModel,
    content: dict[str, Any] | str,
    stop_reason: str,
) -> None:
    """Test the suggest todo subtasks route 502 on an answer out of the schema."""
    fake_chat_model.answer(content, stop_reason=stop_reason)
    async_client.login(bob_member_user)
    response = await async_client.post(
        f"/api/v1/todos/todo/{bob_report_todo.id}/subtask-suggestions/"
    )
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "The AI answered in an unexpected format",
                "errorCode": "AI_INVALID_RESPONSE",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    "status_code",
    [None, 429, 500, 529],
    ids=["timeout", "rate_limited", "server_error", "overloaded"],
)
async def test_suggest_todo_subtasks_route_503(
    async_client: AsyncClient,
    bob_member_user: User,
    bob_report_todo: Todo,
    fake_chat_model: FakeChatModel,
    log_events: Callable[[str], list[dict[str, Any]]],
    status_code: int | None,
) -> None:
    """Test the suggest todo subtasks route 503 when the model cannot answer."""
    fake_chat_model.fail(status_code)
    async_client.login(bob_member_user)
    response = await async_client.post(
        f"/api/v1/todos/todo/{bob_report_todo.id}/subtask-suggestions/"
    )
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "The AI service is unavailable, try again later",
                "errorCode": "AI_UNAVAILABLE",
            }
        }
    )
    assert len(log_events("ai_unavailable")) == 1
