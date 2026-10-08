"""Fixtures shared across all tests."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.core.models  # noqa: F401  # side-effect: register models with SQLModel.metadata
from tests.app import test_app

pytest_plugins: list[str] = [
    "tests.pytest_plugins.database",
]


@pytest_asyncio.fixture(loop_scope="function")
async def async_client() -> AsyncGenerator[AsyncClient]:
    """Return an async API client."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://localhost"
    ) as client:
        yield client
