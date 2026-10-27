"""The analytics events tests: the moments the services record."""

from datetime import date
from uuid import UUID

import pytest
from fastapi import status

from app.emails.services import EmailMessage
from app.users.models import User
from tests.factories.users import TEST_PASSWORD
from tests.pytest_plugins.analytics import FakeAnalytics
from tests.pytest_plugins.auth import FakeIdentityProvider
from tests.utils import AsyncClient, email_token


@pytest.mark.asyncio(loop_scope="function")
async def test_register_and_verify_email_events(
    async_client: AsyncClient,
    email_outbox: list[EmailMessage],
    fake_analytics: FakeAnalytics,
) -> None:
    """Test a sign-up with a password, then the email verification, are recorded."""
    response = await async_client.post(
        "/api/v1/auth/register/",
        json={"email": "new@example.com", "password": TEST_PASSWORD, "firstName": "N"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    user_id = UUID(response.json()["id"])
    assert fake_analytics.events == [
        ("user_signed_up", user_id, {"method": "password"})
    ]
    response = await async_client.post(
        "/api/v1/auth/email/verify/", json={"token": email_token(email_outbox[0])}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert fake_analytics.events[1:] == [("email_verified", user_id, {})]


@pytest.mark.asyncio(loop_scope="function")
async def test_google_sign_up_event(
    async_client: AsyncClient,
    google_identity_provider: FakeIdentityProvider,
    fake_analytics: FakeAnalytics,
) -> None:
    """Test the first Google sign-in is a sign-up, and the next ones are not."""
    tokens = await async_client.google_login()
    await async_client.google_login()
    response = await async_client.get(
        "/api/v1/users/user/me/",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    user_id = UUID(response.json()["id"])
    assert fake_analytics.events == [("user_signed_up", user_id, {"method": "google"})]


@pytest.mark.asyncio(loop_scope="function")
async def test_create_todo_event(
    async_client: AsyncClient, bob_member_user: User, fake_analytics: FakeAnalytics
) -> None:
    """Test a new todo is recorded without its text."""
    async_client.login(bob_member_user)
    response = await async_client.post(
        "/api/v1/todos/todo/",
        json={
            "title": "Call the bank",
            "priority": "high",
            "dueDate": str(date.today()),
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert fake_analytics.events == [
        (
            "todo_created",
            bob_member_user.id,
            {"priority": "high", "has_due_date": True},
        )
    ]
