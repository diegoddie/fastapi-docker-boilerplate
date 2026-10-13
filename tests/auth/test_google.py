"""The Google sign-in routes tests."""

from dataclasses import replace

import pytest
from dirty_equals import IsStr
from fastapi import status
from inline_snapshot import snapshot
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.identity import (
    IdentityProviderUnavailableError,
    InvalidIdentityTokenError,
)
from app.auth.models import ExternalIdentity
from app.core.config import settings
from app.users.models import User
from tests.factories.users import TEST_PASSWORD_HASH
from tests.pytest_plugins.auth import FakeIdentityProvider
from tests.utils import AsyncClient


@pytest.mark.asyncio(loop_scope="function")
async def test_login_google_user_route_200_new_user(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    google_identity_provider: FakeIdentityProvider,
) -> None:
    """Test the first Google sign-in creates a member without a password."""
    tokens = await async_client.google_login()
    assert tokens == snapshot(
        {
            "access_token": IsStr,
            "token_type": "bearer",
            "expires_in": 900,
            "refresh_token": IsStr,
        }
    )
    response = await async_client.get(
        "/api/v1/users/user/me/",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.json()["email"] == "erin.example@gmail.com"
    async_db_session.expunge_all()
    user = (
        await async_db_session.exec(
            select(User).where(User.email == "erin.example@gmail.com")
        )
    ).one()
    assert (user.first_name, user.last_name, user.groups) == (
        "Erin",
        "Example",
        ["member"],
    )
    assert user.password_hash is None
    identity = (await async_db_session.exec(select(ExternalIdentity))).one()
    assert (identity.user_id, identity.provider, identity.subject) == (
        user.id,
        "google",
        "google-subject-erin",
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_login_google_user_route_200_returning_user(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    google_identity_provider: FakeIdentityProvider,
) -> None:
    """Test signing in again finds the same user, even if the email changed."""
    await async_client.google_login()
    google_identity_provider.claims = replace(
        google_identity_provider.claims,
        email="erin.new@gmail.com",
        email_verified=False,
    )
    await async_client.google_login()
    users = (await async_db_session.exec(select(User))).all()
    assert [user.email for user in users] == ["erin.example@gmail.com"]
    assert len((await async_db_session.exec(select(ExternalIdentity))).all()) == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_login_google_user_route_200_links_existing_account(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    google_identity_provider: FakeIdentityProvider,
    bob_member_user: User,
) -> None:
    """Test a verified Google email is linked to the account with that email."""
    google_identity_provider.claims = replace(
        google_identity_provider.claims, email="Bob@Example.com"
    )
    tokens = await async_client.google_login()
    response = await async_client.get(
        "/api/v1/users/user/me/",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.json()["id"] == str(bob_member_user.id)
    async_db_session.expunge_all()
    identity = (await async_db_session.exec(select(ExternalIdentity))).one()
    assert identity.user_id == bob_member_user.id
    user = await async_db_session.get(User, bob_member_user.id)
    assert user is not None
    assert user.password_hash == TEST_PASSWORD_HASH


@pytest.mark.asyncio(loop_scope="function")
async def test_login_google_user_route_401_email_not_verified(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    google_identity_provider: FakeIdentityProvider,
    bob_member_user: User,
) -> None:
    """Test an unverified email can neither create nor take over an account."""
    google_identity_provider.claims = replace(
        google_identity_provider.claims, email="bob@example.com", email_verified=False
    )
    response = await async_client.post(
        "/api/v1/auth/google/", json={"id_token": "google-id-token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "The email of the external account is not verified.",
                "errorCode": "EMAIL_NOT_VERIFIED",
            }
        }
    )
    assert (await async_db_session.exec(select(ExternalIdentity))).all() == []


@pytest.mark.asyncio(loop_scope="function")
async def test_login_google_user_route_401_disabled_user(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    google_identity_provider: FakeIdentityProvider,
    dave_disabled_user: User,
) -> None:
    """Test a disabled account cannot sign in, nor gets a Google link."""
    google_identity_provider.claims = replace(
        google_identity_provider.claims, email="dave@example.com"
    )
    response = await async_client.post(
        "/api/v1/auth/google/", json={"id_token": "google-id-token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"]["errorCode"] == "INVALID_CREDENTIALS"
    assert (await async_db_session.exec(select(ExternalIdentity))).all() == []


@pytest.mark.asyncio(loop_scope="function")
async def test_login_google_user_route_401_disabled_after_linking(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    google_identity_provider: FakeIdentityProvider,
) -> None:
    """Test a user disabled after the first sign-in cannot sign in again."""
    await async_client.google_login()
    user = (await async_db_session.exec(select(User))).one()
    user.datetime_disabled = user.datetime_created
    async_db_session.add(user)
    await async_db_session.commit()
    response = await async_client.post(
        "/api/v1/auth/google/", json={"id_token": "google-id-token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"]["errorCode"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        (
            InvalidIdentityTokenError(),
            status.HTTP_401_UNAUTHORIZED,
            "INVALID_ID_TOKEN",
        ),
        (
            IdentityProviderUnavailableError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "IDENTITY_PROVIDER_UNAVAILABLE",
        ),
    ],
    ids=["invalid_token", "google_unavailable"],
)
async def test_login_google_user_route_errors(
    async_client: AsyncClient,
    google_identity_provider: FakeIdentityProvider,
    error: Exception,
    status_code: int,
    error_code: str,
) -> None:
    """Test a rejected token and an unreachable Google give different errors."""
    google_identity_provider.error = error
    response = await async_client.post(
        "/api/v1/auth/google/", json={"id_token": "google-id-token"}
    )
    assert response.status_code == status_code
    assert response.json()["detail"]["errorCode"] == error_code


@pytest.mark.asyncio(loop_scope="function")
async def test_login_google_user_route_404_disabled(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test Google sign-in answers 404 until a client id is configured."""
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    response = await async_client.post(
        "/api/v1/auth/google/", json={"id_token": "google-id-token"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"]["errorCode"] == "GOOGLE_SIGN_IN_DISABLED"


@pytest.mark.asyncio(loop_scope="function")
async def test_google_test_page_route_200(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the local test page embeds the client id and the API URLs."""
    monkeypatch.setattr(settings, "DOCS_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", 'client-id"><script>')
    response = await async_client.get("/api/v1/auth/google/test-page/")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-client_id="client-id&quot;&gt;&lt;script&gt;"' in response.text
    assert 'data-login-url="/api/v1/auth/google/"' in response.text
    assert 'data-me-url="/api/v1/users/user/me/"' in response.text


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("docs_enabled", "client_id"),
    [(False, "client-id"), (True, None)],
    ids=["docs_disabled", "google_disabled"],
)
async def test_google_test_page_route_404(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    docs_enabled: bool,
    client_id: str | None,
) -> None:
    """Test the test page is served only locally and with Google configured."""
    monkeypatch.setattr(settings, "DOCS_ENABLED", docs_enabled)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", client_id)
    response = await async_client.get("/api/v1/auth/google/test-page/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
