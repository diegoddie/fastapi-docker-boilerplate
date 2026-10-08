"""The FastAPI application main module."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.core.config import Settings, settings
from app.core.database import session_manager
from app.core.handlers import register_exceptions_handlers

try:
    import sentry_sdk
except ModuleNotFoundError:  # pragma: no cover
    pass
else:  # pragma: no cover
    # Why: sentry-sdk is installed only in the `remote` dependency group. The DSN
    # is read from SENTRY_DSN and the FastAPI integration is enabled automatically.
    sentry_sdk.init()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Perform pre/post app run operations."""
    yield
    await session_manager.aclose()


def create_app(app_settings: Settings = settings) -> FastAPI:
    """
    Build the FastAPI application.

    Why: the app and the tests use this same factory, so they cannot drift apart.
    """
    app = FastAPI(
        title="FastAPI Docker Boilerplate",
        description="A production-ready FastAPI backend boilerplate.",
        version=app_settings.VERSION,
        debug=app_settings.DEBUG,
        docs_url=app_settings.DOCS_URL,
        openapi_url=app_settings.OPENAPI_URL,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=app_settings.API_ROOT)
    register_exceptions_handlers(app)
    return app


app = create_app()
