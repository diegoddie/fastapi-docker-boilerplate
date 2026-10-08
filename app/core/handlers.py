"""
The core handlers.

Every error leaves the API in the same shape, so clients can rely on it:

    {"detail": {"message": "...", "errorCode": "NOT_FOUND"}}

Validation errors add an ``errors`` list with one entry per invalid field.
"""

import logging
from typing import cast

from fastapi import FastAPI, Request, Response, status
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
)
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from psycopg.errors import ForeignKeyViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    BaseHTTPException,
    ConflictHTTPException,
    ServerErrorHTTPException,
    UnprocessableHTTPException,
)

logger = logging.getLogger(__name__)

ERROR_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "UNPROCESSABLE",
    status.HTTP_429_TOO_MANY_REQUESTS: "TOO_MANY_REQUESTS",
}


def error_detail(message: str, error_code: str, **extra: object) -> dict[str, object]:
    """Return the ``detail`` of an error response."""
    return {"message": message, "errorCode": error_code, **extra}


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    """Wrap framework HTTP errors (e.g. unknown route, wrong method) in our format."""
    http_exc = cast(StarletteHTTPException, exc)
    if not isinstance(http_exc, BaseHTTPException):
        http_exc = HTTPException(
            status_code=http_exc.status_code,
            detail=error_detail(
                str(http_exc.detail),
                ERROR_CODES.get(http_exc.status_code, "HTTP_ERROR"),
            ),
            headers=http_exc.headers,
        )
    return await default_http_exception_handler(request, http_exc)


async def validation_exception_handler(request: Request, exc: Exception) -> Response:
    """Return request validation errors without echoing the submitted values."""
    # Why: FastAPI's default response includes each invalid `input`, which would
    # send passwords and personal data back in the response (and into any logs).
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in cast(RequestValidationError, exc).errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": error_detail(
                "Validation error.", "VALIDATION_ERROR", errors=errors
            )
        },
    )


async def integrity_error_handler(request: Request, exc: Exception) -> Response:
    """Translate database integrity errors into 409/422 responses."""
    # Why: uniqueness and referential integrity are enforced by the database, so
    # services just commit and let violations bubble up to this single place.
    # The database message holds values and table names: it is never returned,
    # and only the violated constraint name is logged.
    http_exc: BaseHTTPException
    match orig := getattr(exc, "orig", None):
        case UniqueViolation():
            http_exc = ConflictHTTPException(
                message="A resource with the same unique values already exists."
            )
        case ForeignKeyViolation():
            http_exc = UnprocessableHTTPException(
                message="A referenced resource does not exist."
            )
        case NotNullViolation():
            http_exc = UnprocessableHTTPException(
                message="A required value is missing."
            )
        case _:
            http_exc = ServerErrorHTTPException(message="Database integrity error.")
    logger.warning(
        "Integrity error on constraint %s",
        getattr(getattr(orig, "diag", None), "constraint_name", None),
    )
    return await default_http_exception_handler(request, http_exc)


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Return unexpected errors in our format (the traceback is still logged)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_detail("Internal server error.", "SERVER_ERROR")},
    )


def register_exceptions_handlers(app: FastAPI) -> None:
    """Register exceptions handlers."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
