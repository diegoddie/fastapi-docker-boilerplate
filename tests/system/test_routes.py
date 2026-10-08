"""The API system routes tests."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from pytest_mock import AsyncMockType, MockerFixture
from sqlalchemy.exc import OperationalError

from app.core.database import aget_db_session


@pytest.fixture
def db_session_mock(test_app: FastAPI, mocker: MockerFixture) -> AsyncMockType:
    """Override the database session with a mock."""
    session: AsyncMockType = mocker.AsyncMock()

    async def aget_db_session_override() -> AsyncGenerator[AsyncMockType]:
        yield session

    test_app.dependency_overrides[aget_db_session] = aget_db_session_override
    return session


@pytest.mark.asyncio(loop_scope="function")
async def test_health_route_200(async_client: AsyncClient) -> None:
    """Test the health route 200 for GET and HEAD."""
    response = await async_client.get("/api/health/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True
    response = await async_client.head("/api/health/")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b""


@pytest.mark.asyncio(loop_scope="function")
async def test_ready_route_200(
    async_client: AsyncClient, db_session_mock: AsyncMockType
) -> None:
    """Test the ready route 200 when the database answers."""
    response = await async_client.get("/api/ready/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True
    db_session_mock.execute.assert_awaited_once()


@pytest.mark.asyncio(loop_scope="function")
async def test_ready_route_503(
    async_client: AsyncClient, db_session_mock: AsyncMockType
) -> None:
    """Test the ready route 503 when the database is not reachable."""
    db_session_mock.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection refused")
    )
    response = await async_client.get("/api/ready/")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "detail": {
            "message": "The database is not reachable.",
            "errorCode": "SERVICE_UNAVAILABLE",
        }
    }
