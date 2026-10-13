"""The database fixtures."""

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.interfaces import Dialect

from app.core.database import DatabaseSessionManager


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
