"""The core database."""

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings


class DatabaseSessionManager:
    """A database session manager."""

    def __init__(self, host: str, **kwargs: Any):
        """Initialize the instance."""
        self.aengine: AsyncEngine | None = create_async_engine(host, **kwargs)
        self.asession_maker: async_sessionmaker[AsyncSession] | None = (
            async_sessionmaker(
                class_=AsyncSession,
                autocommit=False,
                bind=self.aengine,
                expire_on_commit=False,
            )
        )

    async def aclose(self) -> None:
        """Dispose the engine and release the session maker."""
        if self.aengine is not None:
            await self.aengine.dispose()
            self.aengine = None
        self.asession_maker = None

    @asynccontextmanager
    async def aget_session(self) -> AsyncIterator[AsyncSession]:
        """Create an async session, rolling back on errors and closing on exit."""
        if self.asession_maker is None:
            raise RuntimeError("DatabaseSessionManager is not initialized")
        session = self.asession_maker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


session_manager = DatabaseSessionManager(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)


async def aget_db_session() -> AsyncGenerator[AsyncSession]:
    """Return an async database session."""
    async with session_manager.aget_session() as session:
        yield session


AsyncDBSession = Annotated[AsyncSession, Depends(aget_db_session)]
