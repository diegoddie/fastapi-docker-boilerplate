"""The main module tests."""

import pytest
from fastapi import FastAPI
from pytest_mock import MockerFixture

from app.main import app, lifespan


@pytest.mark.asyncio(loop_scope="function")
async def test_lifespan(mocker: MockerFixture) -> None:
    """Test the database engine is disposed on shutdown."""
    session_manager = mocker.patch("app.main.session_manager", mocker.AsyncMock())
    async with lifespan(FastAPI()):
        session_manager.aclose.assert_not_awaited()
    session_manager.aclose.assert_awaited_once()


def test_app_docs_urls() -> None:
    """Test the docs are served under the API root."""
    assert app.docs_url == "/api/docs"
    assert app.openapi_url == "/api/openapi.json"
