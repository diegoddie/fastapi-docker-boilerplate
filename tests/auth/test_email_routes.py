"""The email verification and password reset routes tests."""

from datetime import UTC, datetime, timedelta

import pytest
from dirty_equals import IsDatetime
from fastapi import status
from inline_snapshot import snapshot
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from time_machine import TimeMachineFixture

from app.auth.models import ExternalIdentity
from app.core.config import settings
from app.emails.services import EmailMessage
from app.users.models import User
from tests.factories.users import TEST_PASSWORD, UserFactory
from tests.utils import AsyncClient, email_token


@pytest.mark.asyncio(loop_scope="function")
async def test_register_user_route_201_verification_email(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    email_outbox: list[EmailMessage],
) -> None:
    """Test a new member gets an email to verify the address, once registered."""
    response = await async_client.post(
        "/api/v1/auth/register/",
        json={
            "email": "new@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Neo",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["isEmailVerified"] is False
    (message,) = email_outbox
    assert (message.to, message.subject) == (
        "new@example.com",
        "Verify your email address",
    )
    assert f"{settings.FRONTEND_URL}/verify-email#token=" in message.text
    response = await async_client.post(
        "/api/v1/auth/email/verify/", json={"token": email_token(message)}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    user = (
        await async_db_session.exec(select(User).where(User.email == "new@example.com"))
    ).one()
    assert user.datetime_email_verified == IsDatetime


@pytest.mark.asyncio(loop_scope="function")
async def test_verify_email_route_400_used_twice(
    async_client: AsyncClient, email_outbox: list[EmailMessage]
) -> None:
    """Test a verification link works once."""
    await async_client.post(
        "/api/v1/auth/register/",
        json={
            "email": "new@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Neo",
        },
    )
    token = email_token(email_outbox[0])
    for status_code in (status.HTTP_204_NO_CONTENT, status.HTTP_400_BAD_REQUEST):
        response = await async_client.post(
            "/api/v1/auth/email/verify/", json={"token": token}
        )
        assert response.status_code == status_code
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "Invalid or expired token.",
                "errorCode": "INVALID_TOKEN",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_verify_email_route_400_expired(
    async_client: AsyncClient,
    email_outbox: list[EmailMessage],
    time_machine: TimeMachineFixture,
) -> None:
    """Test a verification link expires."""
    await async_client.post(
        "/api/v1/auth/register/",
        json={
            "email": "new@example.com",
            "password": TEST_PASSWORD,
            "firstName": "Neo",
        },
    )
    time_machine.move_to(
        datetime.now(UTC)
        + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS, seconds=1)
    )
    response = await async_client.post(
        "/api/v1/auth/email/verify/", json={"token": email_token(email_outbox[0])}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio(loop_scope="function")
async def test_verify_email_route_400_other_purpose(
    async_client: AsyncClient,
    bob_member_user: User,
    email_outbox: list[EmailMessage],
) -> None:
    """Test a password reset token cannot verify an address."""
    await async_client.post(
        "/api/v1/auth/password/forgot/", json={"email": "bob@example.com"}
    )
    response = await async_client.post(
        "/api/v1/auth/email/verify/", json={"token": email_token(email_outbox[0])}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio(loop_scope="function")
async def test_request_email_verification_route_202(
    async_client: AsyncClient,
    user_factory: type[UserFactory],
    email_outbox: list[EmailMessage],
) -> None:
    """Test a new link replaces the previous one."""
    user = await user_factory.create_async(datetime_email_verified=None)
    async_client.login(user)
    for _ in range(2):
        response = await async_client.post("/api/v1/auth/email/verification/")
        assert response.status_code == status.HTTP_202_ACCEPTED
    old, new = email_outbox
    assert old.to == new.to == user.email
    for message, status_code in [
        (old, status.HTTP_400_BAD_REQUEST),
        (new, status.HTTP_204_NO_CONTENT),
    ]:
        response = await async_client.post(
            "/api/v1/auth/email/verify/", json={"token": email_token(message)}
        )
        assert response.status_code == status_code


@pytest.mark.asyncio(loop_scope="function")
async def test_request_email_verification_route_202_already_verified(
    async_client: AsyncClient,
    bob_member_user: User,
    email_outbox: list[EmailMessage],
) -> None:
    """Test no email is sent to an address already verified."""
    async_client.login(bob_member_user)
    response = await async_client.post("/api/v1/auth/email/verification/")
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert email_outbox == []


@pytest.mark.asyncio(loop_scope="function")
async def test_request_email_verification_route_401(async_client: AsyncClient) -> None:
    """Test only a signed-in user can ask for a verification link."""
    response = await async_client.post("/api/v1/auth/email/verification/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_forgot_password_route_202(
    async_client: AsyncClient,
    bob_member_user: User,
    email_outbox: list[EmailMessage],
) -> None:
    """Test a user gets a link to choose a new password."""
    response = await async_client.post(
        "/api/v1/auth/password/forgot/", json={"email": "Bob@Example.com"}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    (message,) = email_outbox
    assert (message.to, message.subject) == ("bob@example.com", "Reset your password")
    assert f"{settings.FRONTEND_URL}/reset-password#token=" in message.text


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    "email", ["nobody@example.com", "dave@example.com"], ids=["unknown", "disabled"]
)
async def test_forgot_password_route_202_no_email(
    async_client: AsyncClient,
    dave_disabled_user: User,
    email_outbox: list[EmailMessage],
    email: str,
) -> None:
    """Test the answer is the same when no active user has the email."""
    response = await async_client.post(
        "/api/v1/auth/password/forgot/", json={"email": email}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert email_outbox == []


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("url", "authenticated"),
    [
        ("/api/v1/auth/password/forgot/", False),
        ("/api/v1/auth/email/verification/", True),
    ],
    ids=["forgot_password", "email_verification"],
)
async def test_email_routes_429_per_recipient(
    async_client: AsyncClient,
    user_factory: type[UserFactory],
    monkeypatch: pytest.MonkeyPatch,
    start_of_minute: datetime,
    url: str,
    authenticated: bool,
) -> None:
    """Test the emails sent to an address are limited, whatever the IP."""
    monkeypatch.setattr(settings, "RATE_LIMIT_EMAILS_PER_HOUR", 1)
    user = await user_factory.create_async(datetime_email_verified=None)
    if authenticated:
        async_client.login(user)
    for status_code in (status.HTTP_202_ACCEPTED, status.HTTP_429_TOO_MANY_REQUESTS):
        response = await async_client.post(url, json={"email": user.email})
        assert response.status_code == status_code
    assert response.headers["Retry-After"] == "3600"


@pytest.mark.asyncio(loop_scope="function")
async def test_reset_password_route_204(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    bob_member_user: User,
    email_outbox: list[EmailMessage],
) -> None:
    """Test a new password replaces the old one and ends every session."""
    session_tokens = await async_client.password_login("bob@example.com")
    await async_client.post(
        "/api/v1/auth/password/forgot/", json={"email": "bob@example.com"}
    )
    response = await async_client.post(
        "/api/v1/auth/password/reset/",
        json={"token": email_token(email_outbox[0]), "password": "a-brand-new-one"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    await async_client.password_login("bob@example.com", "a-brand-new-one")
    response = await async_client.post(
        "/api/v1/auth/login/",
        data={"username": "bob@example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response = await async_client.post(
        "/api/v1/auth/refresh/",
        json={"refresh_token": session_tokens["refresh_token"]},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_reset_password_route_204_unverified_account(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    user_factory: type[UserFactory],
    email_outbox: list[EmailMessage],
) -> None:
    """Test the owner of the address takes over an account nobody verified."""
    user = await user_factory.create_async(datetime_email_verified=None)
    async_db_session.add(
        ExternalIdentity(user_id=user.id, provider="google", subject="someone-else")
    )
    await async_db_session.commit()
    await async_client.post("/api/v1/auth/password/forgot/", json={"email": user.email})
    response = await async_client.post(
        "/api/v1/auth/password/reset/",
        json={"token": email_token(email_outbox[0]), "password": "a-brand-new-one"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    assert (await async_db_session.exec(select(ExternalIdentity))).all() == []
    reloaded = await async_db_session.get(User, user.id)
    assert reloaded is not None
    assert reloaded.datetime_email_verified == IsDatetime


@pytest.mark.asyncio(loop_scope="function")
async def test_reset_password_route_400(async_client: AsyncClient) -> None:
    """Test an unknown token cannot reset a password."""
    response = await async_client.post(
        "/api/v1/auth/password/reset/",
        json={"token": "never-issued", "password": "a-brand-new-one"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"]["errorCode"] == "INVALID_TOKEN"
