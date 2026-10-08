"""The core handlers tests."""

import json

import pytest
from fastapi import FastAPI, Request, status
from httpx import ASGITransport, AsyncClient
from psycopg.errors import ForeignKeyViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.exceptions import NotFoundHTTPException
from app.core.handlers import integrity_error_handler
from app.main import create_app


@pytest.mark.asyncio(loop_scope="function")
async def test_unknown_route_404(async_client: AsyncClient) -> None:
    """Test framework 404 errors use the application error format."""
    response = await async_client.get("/api/unknown/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {"message": "Not Found", "errorCode": "NOT_FOUND"}
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_wrong_method_405(async_client: AsyncClient) -> None:
    """Test framework 405 errors use the application error format."""
    response = await async_client.post("/api/health/")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert set(response.headers["allow"].split(", ")) == {"GET", "HEAD"}
    assert response.json() == {
        "detail": {"message": "Method Not Allowed", "errorCode": "METHOD_NOT_ALLOWED"}
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_application_error(test_app: FastAPI, async_client: AsyncClient) -> None:
    """Test application errors keep their own message and error code."""

    async def missing() -> None:
        """Raise an application error."""
        raise NotFoundHTTPException(
            message="Todo not found", error_code="TODO_NOT_FOUND"
        )

    test_app.add_api_route("/api/missing/", missing)
    response = await async_client.get("/api/missing/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {"message": "Todo not found", "errorCode": "TODO_NOT_FOUND"}
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_validation_error_422(
    test_app: FastAPI, async_client: AsyncClient
) -> None:
    """Test validation errors list the invalid fields without echoing the input."""

    async def search(limit: int) -> int:
        """Return the limit."""
        return limit  # pragma: no cover

    test_app.add_api_route("/api/search/", search)
    response = await async_client.get("/api/search/", params={"limit": "secret"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == {
        "detail": {
            "message": "Validation error.",
            "errorCode": "VALIDATION_ERROR",
            "errors": [
                {
                    "field": "query.limit",
                    "message": (
                        "Input should be a valid integer, "
                        "unable to parse string as an integer"
                    ),
                    "type": "int_parsing",
                }
            ],
        }
    }
    assert "secret" not in response.text


@pytest.mark.asyncio(loop_scope="function")
async def test_unhandled_error_500() -> None:
    """Test unexpected errors become a generic 500 in the application format."""
    # Why: in debug mode Starlette answers with the traceback instead.
    application = create_app(Settings(DEBUG=False))

    async def boom() -> None:
        """Raise an unexpected error."""
        raise RuntimeError("boom")

    application.add_api_route("/api/boom/", boom)
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/api/boom/")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": {"message": "Internal server error.", "errorCode": "SERVER_ERROR"}
    }


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("orig", "status_code", "message", "error_code"),
    [
        (
            UniqueViolation(),
            status.HTTP_409_CONFLICT,
            "A resource with the same unique values already exists.",
            "CONFLICT",
        ),
        (
            ForeignKeyViolation(),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "A referenced resource does not exist.",
            "UNPROCESSABLE",
        ),
        (
            NotNullViolation(),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "A required value is missing.",
            "UNPROCESSABLE",
        ),
        (
            Exception(),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Database integrity error.",
            "SERVER_ERROR",
        ),
    ],
    ids=["unique", "foreign_key", "not_null", "other"],
)
async def test_integrity_error_handler(
    orig: Exception, status_code: int, message: str, error_code: str
) -> None:
    """Test integrity errors are translated without leaking database details."""
    response = await integrity_error_handler(
        Request({"type": "http"}), IntegrityError("INSERT ...", {}, orig)
    )
    assert response.status_code == status_code
    assert json.loads(bytes(response.body)) == {
        "detail": {"message": message, "errorCode": error_code}
    }
