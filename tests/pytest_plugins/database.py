"""The database fixtures."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from pytest_mock import AsyncMockType, MockerFixture
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.interfaces import Dialect
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import DatabaseSessionManager, aget_db_session


@pytest.fixture
def database_session_manager(mocker: MockerFixture) -> DatabaseSessionManager:
    """Return a database session manager backed by a mocked engine."""
    mocker.patch(
        "app.core.database.create_async_engine", return_value=mocker.AsyncMock()
    )
    return DatabaseSessionManager("postgresql+psycopg://user:password@localhost/db")


@pytest.fixture
def postgresql_dialect() -> Dialect:
    """Return the PostgreSQL dialect, to test column types without a database."""
    return postgresql.dialect()  # type: ignore[no-untyped-call]


@pytest.fixture
def db_session_mock(
    test_app: FastAPI, async_db_session: AsyncSession, mocker: MockerFixture
) -> AsyncMockType:
    """Override the test database session with a mock, to simulate failures."""
    session: AsyncMockType = mocker.AsyncMock()

    async def aget_db_session_override() -> AsyncGenerator[AsyncMockType]:
        yield session

    test_app.dependency_overrides[aget_db_session] = aget_db_session_override
    return session
