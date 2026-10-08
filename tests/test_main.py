"""The main module tests."""

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture

from app.core.config import Settings, get_project_version
from app.main import create_app, lifespan


@pytest.mark.asyncio(loop_scope="function")
async def test_lifespan(mocker: MockerFixture) -> None:
    """Test the database engine is disposed on shutdown."""
    session_manager = mocker.patch("app.main.session_manager", mocker.AsyncMock())
    async with lifespan(FastAPI()):
        session_manager.aclose.assert_not_awaited()
    session_manager.aclose.assert_awaited_once()


def test_create_app_version() -> None:
    """Test the app exposes the version declared in pyproject.toml."""
    assert create_app().version == get_project_version()


def test_create_app_docs_local() -> None:
    """Test the docs are served under the API root in local environments."""
    application = create_app(Settings(ENVIRONMENT="local"))
    assert application.docs_url == "/api/docs"
    assert application.openapi_url == "/api/openapi.json"


def test_create_app_docs_remote() -> None:
    """Test the docs are not served in remote environments by default."""
    application = create_app(Settings(ENVIRONMENT="remote"))
    assert application.docs_url is None
    assert application.openapi_url is None


@pytest.mark.asyncio(loop_scope="function")
async def test_create_app_cors() -> None:
    """Test CORS preflight requests from allowed origins are accepted."""
    application = create_app(Settings(CORS_ALLOWED_ORIGINS=["http://localhost:3000"]))
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://localhost"
    ) as client:
        response = await client.options(
            "/api/health/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
