"""The core middleware tests."""

import asyncio
from collections.abc import Callable
from typing import Any

import pytest
from dirty_equals import IsDatetime, IsFloat, IsStr
from fastapi import BackgroundTasks, FastAPI, status
from pytest_mock import MockerFixture

from app.core.middleware import RequestContextMiddleware
from app.users.models import User
from tests.utils import AsyncClient


@pytest.mark.asyncio(loop_scope="function")
async def test_request_logged_with_new_request_id(
    async_client: AsyncClient,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test a request gets a new id, returned in a header and in its log line."""
    response = await async_client.get("/api/unknown/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    request_id = response.headers["X-Request-ID"]
    assert request_id == IsStr(regex=r"[0-9a-f]{32}")
    assert log_events("http_request") == [
        {
            "event": "http_request",
            "method": "GET",
            "path": "/api/unknown/",
            "status_code": status.HTTP_404_NOT_FOUND,
            "duration_ms": IsFloat(ge=0),
            "request_id": request_id,
            "logger": "app.core.middleware",
            "level": "info",
            "timestamp": IsDatetime(iso_string=True),
        }
    ]


@pytest.mark.asyncio(loop_scope="function")
async def test_request_id_from_client(
    async_client: AsyncClient,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test a valid request id sent by the client is kept."""
    response = await async_client.get(
        "/api/unknown/", headers={"X-Request-ID": "frontend-42.a_b"}
    )
    assert response.headers["X-Request-ID"] == "frontend-42.a_b"
    assert log_events("http_request")[-1]["request_id"] == "frontend-42.a_b"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    "request_id", ["has spaces", "x" * 129], ids=["characters", "length"]
)
async def test_request_id_from_client_invalid(
    async_client: AsyncClient, request_id: str
) -> None:
    """Test an unsafe request id sent by the client is replaced by a new one."""
    response = await async_client.get(
        "/api/unknown/", headers={"X-Request-ID": request_id}
    )
    assert response.headers["X-Request-ID"] == IsStr(regex=r"[0-9a-f]{32}")


@pytest.mark.asyncio(loop_scope="function")
async def test_request_logged_with_user_id(
    async_client: AsyncClient,
    bob_member_user: User,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test the log line of an authenticated request says who made it."""
    async_client.login(bob_member_user)
    response = await async_client.get("/api/v1/users/user/me/")
    assert response.status_code == status.HTTP_200_OK
    assert log_events("http_request")[-1]["user_id"] == str(bob_member_user.id)


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("path", ["/api/health/", "/api/ready/"])
async def test_health_checks_logged_at_debug(
    async_client: AsyncClient,
    log_events: Callable[[str], list[dict[str, Any]]],
    path: str,
) -> None:
    """Test health checks log at debug level, so they do not flood the logs."""
    response = await async_client.get(path)
    assert response.status_code == status.HTTP_200_OK
    assert log_events("http_request")[-1]["level"] == "debug"


@pytest.mark.asyncio(loop_scope="function")
async def test_request_duration_excludes_background_tasks(
    test_app: FastAPI,
    async_client: AsyncClient,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test the duration is the time the client waited, not the background work."""

    async def slow_task() -> None:
        """Take a while, after the response."""
        await asyncio.sleep(0.3)

    async def with_task(background_tasks: BackgroundTasks) -> None:
        """Schedule a slow background task."""
        background_tasks.add_task(slow_task)

    test_app.add_api_route("/api/with-task/", with_task)
    await async_client.get("/api/with-task/")
    assert log_events("http_request")[-1]["duration_ms"] < 300


@pytest.mark.asyncio(loop_scope="function")
async def test_non_http_scope(mocker: MockerFixture) -> None:
    """Test lifespan and websocket messages pass through untouched."""
    app, receive, send = mocker.AsyncMock(), mocker.AsyncMock(), mocker.AsyncMock()
    scope = {"type": "lifespan"}
    await RequestContextMiddleware(app)(scope, receive, send)
    app.assert_awaited_once_with(scope, receive, send)
    send.assert_not_awaited()
