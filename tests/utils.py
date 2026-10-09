"""The tests package utils."""

from typing import Any
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport
from httpx import AsyncClient as BaseAsyncClient

from app.auth.dependencies import get_token_subject
from app.users.models import User


class AsyncClient(BaseAsyncClient):
    """An API client that can authenticate as a user without a real token."""

    def __init__(self, app: FastAPI, **kwargs: Any) -> None:
        """Initialize the instance."""
        super().__init__(
            transport=ASGITransport(app=app), base_url="http://localhost", **kwargs
        )
        self.app = app

    def login(self, user: User) -> None:
        """Authenticate the next requests as a user."""

        def get_token_subject_override() -> UUID:
            """Return the id of the logged in user."""
            return user.id

        # Why: only the token decoding is skipped; the user is still loaded from
        # the database, so disabled users are rejected like in production.
        self.app.dependency_overrides[get_token_subject] = get_token_subject_override

    def logout(self) -> None:
        """Send the next requests without authentication."""
        self.app.dependency_overrides.pop(get_token_subject, None)
