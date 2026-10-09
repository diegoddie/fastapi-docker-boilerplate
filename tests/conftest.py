"""Fixtures shared across all tests."""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from faker import Faker
from fastapi import FastAPI
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.core.models  # noqa: F401  # side-effect: register models with SQLModel.metadata
from app.core.config import settings
from app.core.database import DatabaseSessionManager, aget_db_session
from app.main import create_app
from tests.utils import AsyncClient

pytest_plugins: list[str] = [
    "tests.pytest_plugins.database",
    "tests.pytest_plugins.users",
]


@pytest.fixture
def test_app() -> FastAPI:
    """Return a fresh application, so dependency overrides never leak across tests."""
    return create_app()


@pytest_asyncio.fixture(loop_scope="function")
async def async_client(
    test_app: FastAPI, async_db_session: AsyncSession
) -> AsyncGenerator[AsyncClient]:
    """
    Return an async API client.

    Why: it depends on the test database session, so no request can ever reach
    the development database by mistake.
    """
    async with AsyncClient(test_app) as client:
        yield client


def _maintenance_engine(database_url: str) -> Engine:
    """Return an engine on the server's `postgres` database, to create databases."""
    return create_engine(
        make_url(database_url).set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )


@pytest.fixture(scope="session")
def create_db(worker_id: str) -> Generator[str]:
    """Create a test database (one per xdist worker) with the schema."""
    suffix = f"-{worker_id}" if worker_id != "master" else ""
    test_database_url = f"{settings.DATABASE_URL}-test{suffix}"
    engine = _maintenance_engine(test_database_url)
    name = engine.dialect.identifier_preparer.quote(
        str(make_url(test_database_url).database)
    )
    with engine.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
        connection.execute(text(f"CREATE DATABASE {name}"))
    schema_engine = create_engine(test_database_url, poolclass=NullPool)
    SQLModel.metadata.create_all(schema_engine)
    schema_engine.dispose()
    yield test_database_url
    with engine.connect() as connection:
        connection.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_manager(create_db: str) -> Generator[DatabaseSessionManager]:
    """Return a session manager bound to the test database."""
    manager = DatabaseSessionManager(create_db, poolclass=NullPool)
    yield manager
    # Why: the engine is used by per-test event loops and NullPool keeps no open
    # connections, so dropping the references is enough.
    manager.aengine = None
    manager.asession_maker = None


@pytest_asyncio.fixture(loop_scope="function")
async def async_db_session(
    test_app: FastAPI, test_session_manager: DatabaseSessionManager
) -> AsyncGenerator[AsyncSession]:
    """
    Return a database session whose changes are rolled back after the test.

    Why: the test runs inside an outer transaction and the session joins it with
    savepoints, so the services can commit as usual and nothing survives the test.
    """
    assert test_session_manager.aengine is not None
    async with test_session_manager.aengine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async def aget_db_session_override() -> AsyncGenerator[AsyncSession]:
            yield session

        test_app.dependency_overrides[aget_db_session] = aget_db_session_override
        yield session
        await session.close()
        await transaction.rollback()


@pytest.fixture
def faker_seed() -> int:
    """Seed faker, so generated data is the same on every run."""
    return 1


@pytest.fixture
def seed_factories(
    faker: Faker, faker_seed: int, async_db_session: AsyncSession
) -> None:
    """Configure the factories to use the seeded faker and the test session."""
    SQLAlchemyFactory.__faker__ = faker
    SQLAlchemyFactory.__async_session__ = async_db_session
    SQLAlchemyFactory.__random__.seed(faker_seed)
