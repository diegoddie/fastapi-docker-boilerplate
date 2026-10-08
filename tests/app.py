"""
The FastAPI test application.

Same routers and exception handlers as ``app.main.app``, but without the lifespan
(no engine disposal between tests) and without Sentry.
"""

from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import settings
from app.core.handlers import register_exceptions_handlers

test_app = FastAPI(title="FastAPI Docker Boilerplate - test", debug=False)

test_app.include_router(api_router, prefix=settings.API_ROOT)

register_exceptions_handlers(test_app)
