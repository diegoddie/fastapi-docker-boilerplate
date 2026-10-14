"""The auth package router tests."""

from datetime import UTC, datetime, timedelta

import pytest
from dirty_equals import IsDatetime, IsStr, IsUUID
from fastapi import status
from inline_snapshot import snapshot
from sqlmodel import col, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import RefreshToken
from app.auth.security import password_hasher
from app.auth.services import hash_refresh_token
from app.core.config import settings
from app.users.models import User
from tests.factories.users import TEST_PASSWORD, UserFactory
from tests.utils import AsyncClient


@pytest.mark.asyncio(loop_scope="function")
async def test_register_user_route_201(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """Test the register user route 201: a new member with a hashed password."""
    response = await async_client.post(
        "/api/v1/auth/register/",
        json={
            "email": "New.User@Example.com",
            "password": "a-strong-password",
            "firstName": "New",
            "lastName": "User",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == snapshot(
        {
            "email": "new.user@example.com",
            "firstName": "New",
            "lastName": "User",
            "id": IsUUID,
            "groups": ["member"],
            "isActive": True,
            "datetimeCreated": IsDatetime(iso_string=True),
        }
    )
    async_db_session.expunge_all()
    user = (
        await async_db_session.exec(
            select(User).where(User.email == "new.user@example.com")
        )
    ).one()
    assert user.password_hash is not None
    assert user.password_hash != "a-strong-password"
    assert await password_hasher.verify("a-strong-password", user.password_hash)


@pytest.mark.asyncio(loop_scope="function")
async def test_register_user_route_409(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test the register user route 409 for an email already registered."""
    response = await async_client.post(
        "/api/v1/auth/register/",
        json={
            "email": "BOB@example.com",
            "password": "a-strong-password",
            "firstName": "Bob",
            "lastName": "Again",
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "A resource with the same unique values already exists.",
                "errorCode": "CONFLICT",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_register_user_route_422(async_client: AsyncClient) -> None:
    """Test the register user route 422 without echoing the password back."""
    response = await async_client.post(
        "/api/v1/auth/register/",
        json={"email": "not-an-email", "password": "s3cr3t!", "firstName": ""},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "Validation error.",
                "errorCode": "VALIDATION_ERROR",
                "errors": [
                    {
                        "field": "body.email",
                        "message": (
                            "value is not a valid email address: "
                            "An email address must have an @-sign."
                        ),
                        "type": "value_error",
                    },
                    {
                        "field": "body.firstName",
                        "message": "String should have at least 1 character",
                        "type": "string_too_short",
                    },
                    {
                        "field": "body.password",
                        "message": "String should have at least 8 characters",
                        "type": "string_too_short",
                    },
                ],
            }
        }
    )
    assert "s3cr3t!" not in response.text


@pytest.mark.asyncio(loop_scope="function")
async def test_login_user_route_200(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test the login user route 200: a token pair that authenticates requests."""
    tokens = await async_client.password_login("Bob@Example.com")
    assert tokens == snapshot(
        {
            "access_token": IsStr,
            "token_type": "bearer",
            "expires_in": 900,
            "refresh_token": IsStr,
        }
    )
    stored = (await async_db_session.exec(select(RefreshToken))).one()
    assert stored.user_id == bob_member_user.id
    assert stored.token_hash == hash_refresh_token(tokens["refresh_token"])
    assert stored.datetime_revoked is None
    response = await async_client.get(
        "/api/v1/users/user/me/",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "bob@example.com"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("bob@example.com", "wrong-password"),
        ("nobody@example.com", TEST_PASSWORD),
        ("dave@example.com", TEST_PASSWORD),
        ("erin@example.com", TEST_PASSWORD),
    ],
    ids=["wrong_password", "unknown_email", "disabled_user", "no_password"],
)
async def test_login_user_route_401(
    async_client: AsyncClient,
    user_factory: type[UserFactory],
    bob_member_user: User,
    dave_disabled_user: User,
    email: str,
    password: str,
) -> None:
    """Test the login user route 401 gives the same answer for every failure."""
    await user_factory.create_async(email="erin@example.com", password_hash=None)
    response = await async_client.post(
        "/api/v1/auth/login/", data={"username": email, "password": password}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "Invalid email or password.",
                "errorCode": "INVALID_CREDENTIALS",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_refresh_token_route_200(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test the refresh token route 200 rotates the refresh token."""
    first = await async_client.password_login("bob@example.com")
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": first["refresh_token"]}
    )
    assert response.status_code == status.HTTP_200_OK
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    async_db_session.expunge_all()
    old, new = (
        await async_db_session.exec(
            select(RefreshToken).order_by(col(RefreshToken.datetime_created))
        )
    ).all()
    assert old.datetime_revoked == IsDatetime
    assert new.datetime_revoked is None
    assert new.family_id == old.family_id
    response = await async_client.get(
        "/api/v1/users/user/me/",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio(loop_scope="function")
async def test_refresh_token_route_200_concurrent(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test a token rotated moments ago (e.g. by another tab) still gets a pair."""
    first = await async_client.password_login("bob@example.com")
    second = (
        await async_client.post(
            "/api/v1/auth/refresh/", json={"refresh_token": first["refresh_token"]}
        )
    ).json()
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": first["refresh_token"]}
    )
    assert response.status_code == status.HTTP_200_OK
    third = response.json()
    assert third["refresh_token"] != second["refresh_token"]
    for tokens in (second, third):
        response = await async_client.post(
            "/api/v1/auth/refresh/", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio(loop_scope="function")
async def test_refresh_token_route_401_reuse(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test reusing a token rotated before the grace period ends the session."""
    first = await async_client.password_login("bob@example.com")
    second = (
        await async_client.post(
            "/api/v1/auth/refresh/", json={"refresh_token": first["refresh_token"]}
        )
    ).json()
    await async_db_session.exec(
        update(RefreshToken)
        .where(col(RefreshToken.datetime_revoked).is_not(None))
        .values(
            datetime_revoked=datetime.now(UTC)
            - timedelta(seconds=settings.REFRESH_TOKEN_REUSE_GRACE_SECONDS + 1)
        )
    )
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": first["refresh_token"]}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "Invalid or expired refresh token.",
                "errorCode": "INVALID_REFRESH_TOKEN",
            }
        }
    )
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": second["refresh_token"]}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_refresh_token_route_401_reuse_after_logout(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test the grace period does not reopen a session that was ended."""
    first = await async_client.password_login("bob@example.com")
    second = (
        await async_client.post(
            "/api/v1/auth/refresh/", json={"refresh_token": first["refresh_token"]}
        )
    ).json()
    await async_client.post(
        "/api/v1/auth/logout/", json={"refresh_token": second["refresh_token"]}
    )
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": first["refresh_token"]}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_refresh_token_route_401_unknown(async_client: AsyncClient) -> None:
    """Test the refresh token route 401 for a token that was never issued."""
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": "never-issued"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"]["errorCode"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio(loop_scope="function")
async def test_refresh_token_route_401_expired(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test the refresh token route 401 for an expired token."""
    tokens = await async_client.password_login("bob@example.com")
    await async_db_session.exec(
        update(RefreshToken).values(
            datetime_expires=datetime.now(UTC) - timedelta(seconds=1)
        )
    )
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_refresh_token_route_401_disabled_user(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test the refresh token route 401 once the user has been disabled."""
    tokens = await async_client.password_login("bob@example.com")
    bob_member_user.datetime_disabled = datetime.now(UTC)
    async_db_session.add(bob_member_user)
    await async_db_session.commit()
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_logout_user_route_204(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test the logout user route 204 ends only the session of the token."""
    laptop = await async_client.password_login("bob@example.com")
    phone = await async_client.password_login("bob@example.com")
    response = await async_client.post(
        "/api/v1/auth/logout/", json={"refresh_token": laptop["refresh_token"]}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": laptop["refresh_token"]}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response = await async_client.post(
        "/api/v1/auth/refresh/", json={"refresh_token": phone["refresh_token"]}
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio(loop_scope="function")
async def test_logout_user_route_204_unknown(async_client: AsyncClient) -> None:
    """Test the logout user route 204 is idempotent for unknown tokens."""
    response = await async_client.post(
        "/api/v1/auth/logout/", json={"refresh_token": "never-issued"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio(loop_scope="function")
async def test_access_token_401_missing(async_client: AsyncClient) -> None:
    """Test protected routes answer 401 without an access token."""
    response = await async_client.get("/api/v1/users/user/me/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == snapshot(
        {"detail": {"message": "Not authenticated", "errorCode": "UNAUTHORIZED"}}
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_access_token_401_invalid(async_client: AsyncClient) -> None:
    """Test protected routes answer 401 for a malformed access token."""
    response = await async_client.get(
        "/api/v1/users/user/me/", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "Invalid or expired access token.",
                "errorCode": "INVALID_TOKEN",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_access_token_401_disabled_user(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test a valid access token stops working as soon as the user is disabled."""
    tokens = await async_client.password_login("bob@example.com")
    bob_member_user.datetime_disabled = datetime.now(UTC)
    async_db_session.add(bob_member_user)
    await async_db_session.commit()
    response = await async_client.get(
        "/api/v1/users/user/me/",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"]["errorCode"] == "INVALID_TOKEN"
