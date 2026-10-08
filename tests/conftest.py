"""Fixtures shared across all tests."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import app.core.models  # noqa: F401  # side-effect: register models with SQLModel.metadata
from app.main import create_app

pytest_plugins: list[str] = [
    "tests.pytest_plugins.database",
]


@pytest.fixture
def test_app() -> FastAPI:
    """Return a fresh application, so dependency overrides never leak across tests."""
    return create_app()


@pytest_asyncio.fixture(loop_scope="function")
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Return an async API client."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://localhost"
    ) as client:
        yield client
