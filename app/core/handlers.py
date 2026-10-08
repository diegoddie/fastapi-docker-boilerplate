"""The core handlers."""

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from psycopg.errors import ForeignKeyViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    BaseHTTPException,
    ConflictHTTPException,
    ServerErrorHTTPException,
    UnprocessableHTTPException,
)


async def integrity_error_handler(request: Request, exc: Exception) -> Response:
    """Translate database integrity errors into 409/422 responses."""
    # Why: uniqueness and referential integrity are enforced by the database, so
    # services just commit and let violations bubble up to this single place.
    http_exc: BaseHTTPException
    match orig := getattr(exc, "orig", None):
        case UniqueViolation():
            http_exc = ConflictHTTPException(message=orig.diag.message_detail)
        case ForeignKeyViolation() | NotNullViolation():
            http_exc = UnprocessableHTTPException(message=orig.diag.message_detail)
        case _:
            http_exc = ServerErrorHTTPException()
    return await http_exception_handler(request, http_exc)


def register_exceptions_handlers(app: FastAPI) -> None:
    """Register exceptions handlers."""
    app.add_exception_handler(IntegrityError, integrity_error_handler)
