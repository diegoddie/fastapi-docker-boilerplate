"""The core exceptions."""

from typing import Any

from fastapi import status
from fastapi.exceptions import HTTPException


class BaseHTTPException(HTTPException):
    """Base HTTP exception with a machine-readable error code."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: Any | None = None,
        error_code: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Initialize the instance."""
        super().__init__(
            status_code=self.status_code,
            detail={"message": message, "errorCode": error_code or self.error_code},
            headers=headers,
        )


class UnauthorizedHTTPException(BaseHTTPException):
    """Unauthorized http exception."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


class ForbiddenHTTPException(BaseHTTPException):
    """Forbidden http exception."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class NotFoundHTTPException(BaseHTTPException):
    """Not found http exception."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictHTTPException(BaseHTTPException):
    """Conflict http exception."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class UnprocessableHTTPException(BaseHTTPException):
    """Unprocessable content http exception."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "UNPROCESSABLE"


class ServerErrorHTTPException(BaseHTTPException):
    """Server error http exception."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "SERVER_ERROR"
