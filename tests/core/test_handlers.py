"""The core handlers tests."""

import json

import pytest
from fastapi import Request, status
from psycopg.errors import ForeignKeyViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError

from app.core.handlers import integrity_error_handler


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("orig", "status_code", "error_code"),
    [
        (UniqueViolation(), status.HTTP_409_CONFLICT, "CONFLICT"),
        (ForeignKeyViolation(), status.HTTP_422_UNPROCESSABLE_CONTENT, "UNPROCESSABLE"),
        (NotNullViolation(), status.HTTP_422_UNPROCESSABLE_CONTENT, "UNPROCESSABLE"),
        (Exception(), status.HTTP_500_INTERNAL_SERVER_ERROR, "SERVER_ERROR"),
    ],
    ids=["unique", "foreign_key", "not_null", "other"],
)
async def test_integrity_error_handler(
    orig: Exception, status_code: int, error_code: str
) -> None:
    """Test integrity errors are translated into application errors."""
    response = await integrity_error_handler(
        Request({"type": "http"}), IntegrityError("INSERT ...", {}, orig)
    )
    assert response.status_code == status_code
    assert json.loads(bytes(response.body)) == {
        "detail": {"message": None, "errorCode": error_code}
    }
