"""The FastAPI application main module."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from app.api.router import router as api_router
from app.core.config import Settings, get_project_description, settings
from app.core.constants import REQUEST_ID_HEADER
from app.core.database import session_manager
from app.core.handlers import register_exceptions_handlers
from app.core.logs import add_request_id_to_sentry_event, configure_logging
from app.core.middleware import RequestContextMiddleware

configure_logging(settings)

try:
    import sentry_sdk
except ModuleNotFoundError:  # pragma: no cover
    pass
else:  # pragma: no cover
    # Why: sentry-sdk is installed only in the `remote` dependency group. The DSN
    # is read from SENTRY_DSN and the FastAPI integration is enabled automatically.
    sentry_sdk.init(before_send=add_request_id_to_sentry_event)


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
        description=get_project_description(),
        version=app_settings.VERSION,
        debug=app_settings.DEBUG,
        docs_url=app_settings.DOCS_URL,
        openapi_url=app_settings.OPENAPI_URL,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix=app_settings.API_ROOT)
    add_pagination(app)
    register_exceptions_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Why: browsers hide response headers from scripts unless listed here.
        expose_headers=[REQUEST_ID_HEADER],
    )
    # Why: the last middleware added is the outermost, so every request gets an
    # id, including those CORS answers by itself; health checks log at debug
    # level, not to flood the logs every few seconds.
    app.add_middleware(
        RequestContextMiddleware,
        quiet_paths=[str(app.url_path_for(name)) for name in ("health", "ready")],
    )
    return app


app = create_app()
