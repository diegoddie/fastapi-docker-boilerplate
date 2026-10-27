"""The API system routes tests."""

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from pytest_mock import AsyncMockType
from sqlalchemy.exc import OperationalError


@pytest.mark.asyncio(loop_scope="function")
async def test_health_route_200(async_client: AsyncClient) -> None:
    """Test the health route 200."""
    response = await async_client.get("/api/health/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True


@pytest.mark.asyncio(loop_scope="function")
async def test_ready_route_200(async_client: AsyncClient) -> None:
    """Test the ready route 200 when the database answers."""
    response = await async_client.get("/api/ready/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("path", ["/api/health/", "/api/ready/"])
async def test_health_routes_head_200(async_client: AsyncClient, path: str) -> None:
    """Test uptime monitors can probe the health routes with HEAD."""
    response = await async_client.head(path)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio(loop_scope="function")
async def test_ready_route_503(
    async_client: AsyncClient, db_session_mock: AsyncMockType
) -> None:
    """Test the ready route 503 when the database is not reachable."""
    db_session_mock.scalar.side_effect = OperationalError(
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


def test_every_route_requires_authentication(test_app: FastAPI) -> None:
    """Test no route is public by mistake: only the listed paths are public."""
    public_paths = {
        "/api/health/",
        "/api/ready/",
        "/api/v1/auth/register/",
        "/api/v1/auth/login/",
        "/api/v1/auth/refresh/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/google/",
        "/api/v1/auth/email/verify/",
        "/api/v1/auth/password/forgot/",
        "/api/v1/auth/password/reset/",
        # Why: Polar calls it; the signature proves the sender.
        "/api/v1/payments/webhook/",  # copier:payments
    }
    # Why: the OpenAPI schema lists a security requirement for every operation
    # that depends on the bearer token, i.e. exactly what clients will see.
    operations = {
        (path, method): operation
        for path, methods in test_app.openapi()["paths"].items()
        for method, operation in methods.items()
    }
    assert {path for path, _ in operations} >= public_paths
    unprotected = sorted(
        f"{method.upper()} {path}"
        for (path, method), operation in operations.items()
        if path not in public_paths and "security" not in operation
    )
    assert unprotected == []
