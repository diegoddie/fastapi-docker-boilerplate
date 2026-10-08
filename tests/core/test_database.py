"""The core database tests."""

from typing import cast

import pytest
from pytest_mock import AsyncMockType, MockerFixture

from app.core import database
from app.core.database import DatabaseSessionManager, aget_db_session


@pytest.mark.asyncio(loop_scope="function")
async def test_database_session_manager_aclose(
    database_session_manager: DatabaseSessionManager,
) -> None:
    """Test closing the database session manager is idempotent."""
    aengine = cast(AsyncMockType, database_session_manager.aengine)
    await database_session_manager.aclose()
    aengine.dispose.assert_awaited_once()
    assert database_session_manager.aengine is None
    assert database_session_manager.asession_maker is None
    await database_session_manager.aclose()
    aengine.dispose.assert_awaited_once()


@pytest.mark.asyncio(loop_scope="function")
async def test_database_session_manager_aget_session(
    database_session_manager: DatabaseSessionManager, mocker: MockerFixture
) -> None:
    """Test the session is yielded and closed without rollback."""
    session_mock = mocker.AsyncMock()
    # Why: `session is session_mock` narrows the mock to AsyncSession for mypy.
    rollback, close = session_mock.rollback, session_mock.close
    mocker.patch.object(
        database_session_manager,
        "asession_maker",
        mocker.MagicMock(return_value=session_mock),
    )
    async with database_session_manager.aget_session() as session:
        assert session is session_mock
    rollback.assert_not_awaited()
    close.assert_awaited_once()


@pytest.mark.asyncio(loop_scope="function")
async def test_database_session_manager_aget_session_rollback(
    database_session_manager: DatabaseSessionManager, mocker: MockerFixture
) -> None:
    """Test the session is rolled back and closed when an error is raised."""
    session_mock = mocker.AsyncMock()
    mocker.patch.object(
        database_session_manager,
        "asession_maker",
        mocker.MagicMock(return_value=session_mock),
    )
    with pytest.raises(ValueError, match="boom"):
        async with database_session_manager.aget_session():
            raise ValueError("boom")
    session_mock.rollback.assert_awaited_once()
    session_mock.close.assert_awaited_once()


@pytest.mark.asyncio(loop_scope="function")
async def test_database_session_manager_aget_session_not_initialized(
    database_session_manager: DatabaseSessionManager,
) -> None:
    """Test getting a session from a closed manager raises an error."""
    await database_session_manager.aclose()
    with pytest.raises(RuntimeError, match="not initialized"):
        async with database_session_manager.aget_session():
            pass  # pragma: no cover


@pytest.mark.asyncio(loop_scope="function")
async def test_aget_db_session(mocker: MockerFixture) -> None:
    """Test the FastAPI dependency yields a session from the session manager."""
    session_mock = mocker.AsyncMock()
    close = session_mock.close
    mocker.patch.object(
        database.session_manager,
        "asession_maker",
        mocker.MagicMock(return_value=session_mock),
    )
    generator = aget_db_session()
    assert await anext(generator) is session_mock
    with pytest.raises(StopAsyncIteration):
        await anext(generator)
    close.assert_awaited_once()
