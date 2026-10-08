"""The api package router."""

from fastapi import APIRouter

from app.api.v1.router import router as api_v1_router

router = APIRouter()
router.include_router(api_v1_router, prefix="/v1")


@router.api_route("/health/", methods=["GET", "HEAD"], tags=["system"])
async def health() -> bool:
    """Perform a liveness check."""
    return True
