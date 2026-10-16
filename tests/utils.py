"""The tests package utils."""

import re
from typing import Any
from uuid import UUID

from fastapi import FastAPI, status
from httpx import ASGITransport
from httpx import AsyncClient as BaseAsyncClient

from app.auth.dependencies import get_token_subject
from app.emails.services import EmailMessage
from app.users.models import User
from tests.factories.users import TEST_PASSWORD


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

    async def password_login(
        self, email: str, password: str = TEST_PASSWORD
    ) -> dict[str, Any]:
        """Log in through the API with a password and return the tokens."""
        response = await self.post(
            "/api/v1/auth/login/", data={"username": email, "password": password}
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        return dict(response.json())

    async def google_login(self, id_token: str = "google-id-token") -> dict[str, Any]:
        """Log in through the API with a Google ID token and return the tokens."""
        response = await self.post("/api/v1/auth/google/", json={"id_token": id_token})
        assert response.status_code == status.HTTP_200_OK, response.text
        return dict(response.json())


def email_token(message: EmailMessage) -> str:
    """Return the token carried by the link in an email."""
    match = re.search(r"#token=([\w-]+)", message.text)
    assert match is not None, message.text
    return match.group(1)
