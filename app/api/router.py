"""The api package router."""

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import router as api_v1_router
from app.core.database import AsyncDBSession
from app.core.exceptions import ServiceUnavailableHTTPException

router = APIRouter()
router.include_router(api_v1_router, prefix="/v1")


@router.get("/health/", tags=["system"])
async def health() -> bool:
    """Perform a liveness check: the app is up and serving requests."""
    return True


@router.get("/ready/", tags=["system"])
async def ready(session: AsyncDBSession) -> bool:
    """Perform a readiness check: the app can reach the database."""
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        raise ServiceUnavailableHTTPException(
            message="The database is not reachable."
        ) from e
    return True
