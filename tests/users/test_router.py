"""The users package router tests."""

import pytest
from dirty_equals import IsDatetime
from fastapi import status
from inline_snapshot import snapshot
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import RefreshToken
from app.users.models import User
from tests.factories.users import TEST_PASSWORD, UserFactory
from tests.utils import AsyncClient

DUMMY_UUID = "00000000-0000-0000-0000-000000000000"
ME_URL = "/api/v1/users/user/me/"
LIST_URL = "/api/v1/users/user/"


def detail_url(user_id: object) -> str:
    """Return the URL of a user."""
    return f"/api/v1/users/user/{user_id}/"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", ME_URL),
        ("patch", ME_URL),
        ("get", LIST_URL),
        ("get", detail_url(DUMMY_UUID)),
        ("patch", detail_url(DUMMY_UUID)),
        ("delete", detail_url(DUMMY_UUID)),
    ],
    ids=[
        "me_user",
        "update_me_user",
        "list_users",
        "detail_user",
        "update_user",
        "delete_user",
    ],
)
async def test_route_401(async_client: AsyncClient, method: str, url: str) -> None:
    """Test that unauthenticated requests return 401."""
    response = await getattr(async_client, method)(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", LIST_URL),
        ("get", detail_url(DUMMY_UUID)),
        ("patch", detail_url(DUMMY_UUID)),
        ("delete", detail_url(DUMMY_UUID)),
    ],
    ids=["list_users", "detail_user", "update_user", "delete_user"],
)
async def test_route_403(
    async_client: AsyncClient, bob_member_user: User, method: str, url: str
) -> None:
    """Test that requests without the required permission return 403."""
    async_client.login(bob_member_user)
    response = await getattr(async_client, method)(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "You do not have permission to perform this action.",
                "errorCode": "FORBIDDEN",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_me_user_route_200(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test the me user route 200."""
    async_client.login(bob_member_user)
    response = await async_client.get(ME_URL)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == snapshot(
        {
            "email": "bob@example.com",
            "firstName": "Bob",
            "lastName": "Member",
            "id": "0194f8a0-2000-7000-8000-000000000002",
            "groups": ["member"],
            "isActive": True,
            "datetimeCreated": IsDatetime(iso_string=True),
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_update_me_user_route_204(
    async_client: AsyncClient, async_db_session: AsyncSession, bob_member_user: User
) -> None:
    """Test the update me user route 204 changes only the given fields."""
    async_client.login(bob_member_user)
    response = await async_client.patch(ME_URL, json={"firstName": "  Robert  "})
    assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    user = await async_db_session.get(User, bob_member_user.id)
    assert user is not None
    assert (user.first_name, user.last_name) == ("Robert", "Member")


@pytest.mark.asyncio(loop_scope="function")
async def test_update_me_user_route_422(
    async_client: AsyncClient, bob_member_user: User
) -> None:
    """Test the update me user route 422 for an explicit null."""
    async_client.login(bob_member_user)
    response = await async_client.patch(ME_URL, json={"lastName": None})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"]["errors"] == snapshot(
        [
            {
                "field": "body.lastName",
                "message": "Value error, Field cannot be null",
                "type": "value_error",
            }
        ]
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_list_users_route_200(
    async_client: AsyncClient,
    alice_admin_user: User,
    bob_member_user: User,
    carol_viewer_user: User,
    dave_disabled_user: User,
) -> None:
    """Test the list users route 200 is paginated and sorted by email."""
    async_client.login(alice_admin_user)
    response = await async_client.get(LIST_URL, params={"size": 2, "page": 2})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == snapshot(
        {
            "items": [
                {
                    "email": "carol@example.com",
                    "firstName": "Carol",
                    "lastName": "Viewer",
                    "id": "0194f8a0-2000-7000-8000-000000000003",
                    "groups": ["viewer"],
                    "isActive": True,
                    "datetimeCreated": IsDatetime(iso_string=True),
                },
                {
                    "email": "dave@example.com",
                    "firstName": "Dave",
                    "lastName": "Disabled",
                    "id": "0194f8a0-2000-7000-8000-000000000004",
                    "groups": ["member"],
                    "isActive": False,
                    "datetimeCreated": IsDatetime(iso_string=True),
                },
            ],
            "total": 4,
            "page": 2,
            "size": 2,
            "pages": 2,
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_list_users_route_200_default_page(
    async_client: AsyncClient,
    user_factory: type[UserFactory],
    alice_admin_user: User,
) -> None:
    """Test the list users route 200 with the default page size."""
    await user_factory.create_batch_async(3)
    async_client.login(alice_admin_user)
    response = await async_client.get(LIST_URL)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert (data["total"], data["page"], data["size"]) == (4, 1, 50)
    assert [user["email"] for user in data["items"]] == sorted(
        user["email"] for user in data["items"]
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_detail_user_route_200(
    async_client: AsyncClient, alice_admin_user: User, carol_viewer_user: User
) -> None:
    """Test the detail user route 200."""
    async_client.login(alice_admin_user)
    response = await async_client.get(detail_url(carol_viewer_user.id))
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "carol@example.com"


@pytest.mark.asyncio(loop_scope="function")
async def test_detail_user_route_404(
    async_client: AsyncClient, alice_admin_user: User
) -> None:
    """Test the detail user route 404."""
    async_client.login(alice_admin_user)
    response = await async_client.get(detail_url(DUMMY_UUID))
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == snapshot(
        {
            "detail": {
                "message": f"User with id {DUMMY_UUID} not found",
                "errorCode": "USER_NOT_FOUND",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_update_user_route_204(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    alice_admin_user: User,
    bob_member_user: User,
) -> None:
    """Test the update user route 204 changes the groups."""
    async_client.login(alice_admin_user)
    response = await async_client.patch(
        detail_url(bob_member_user.id), json={"groups": ["viewer"]}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    user = await async_db_session.get(User, bob_member_user.id)
    assert user is not None
    assert user.groups == ["viewer"]
    assert user.is_active is True


@pytest.mark.asyncio(loop_scope="function")
async def test_update_user_route_204_reactivate(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    alice_admin_user: User,
    dave_disabled_user: User,
) -> None:
    """Test the update user route 204 reactivates a disabled user."""
    async_client.login(alice_admin_user)
    response = await async_client.patch(
        detail_url(dave_disabled_user.id), json={"datetimeDisabled": None}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    user = await async_db_session.get(User, dave_disabled_user.id)
    assert user is not None
    assert user.is_active is True


@pytest.mark.asyncio(loop_scope="function")
async def test_update_user_route_403_self(
    async_client: AsyncClient, alice_admin_user: User
) -> None:
    """Test the update user route 403 when administrators change their own access."""
    async_client.login(alice_admin_user)
    response = await async_client.patch(
        detail_url(alice_admin_user.id), json={"groups": ["member"]}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == snapshot(
        {
            "detail": {
                "message": "You cannot change your own groups or disable yourself.",
                "errorCode": "SELF_ACCESS_CHANGE",
            }
        }
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_update_user_route_404(
    async_client: AsyncClient, alice_admin_user: User
) -> None:
    """Test the update user route 404."""
    async_client.login(alice_admin_user)
    response = await async_client.patch(detail_url(DUMMY_UUID), json={"groups": []})
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_user_route_204(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    alice_admin_user: User,
    bob_member_user: User,
) -> None:
    """Test the delete user route 204 disables the user and ends their sessions."""
    response = await async_client.post(
        "/api/v1/auth/login/",
        data={"username": "bob@example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    async_client.login(alice_admin_user)
    response = await async_client.delete(detail_url(bob_member_user.id))
    assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    user = await async_db_session.get(User, bob_member_user.id)
    assert user is not None
    assert user.datetime_disabled == IsDatetime
    token = (await async_db_session.exec(select(RefreshToken))).one()
    assert token.datetime_revoked == IsDatetime


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_user_route_403_self(
    async_client: AsyncClient, alice_admin_user: User
) -> None:
    """Test the delete user route 403 when administrators disable themselves."""
    async_client.login(alice_admin_user)
    response = await async_client.delete(detail_url(alice_admin_user.id))
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["errorCode"] == "SELF_ACCESS_CHANGE"


@pytest.mark.asyncio(loop_scope="function")
async def test_logout_from_client(
    async_client: AsyncClient, alice_admin_user: User
) -> None:
    """Test the test client logout removes the authentication."""
    async_client.login(alice_admin_user)
    assert (await async_client.get(ME_URL)).status_code == status.HTTP_200_OK
    async_client.logout()
    assert (await async_client.get(ME_URL)).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="function")
async def test_disabled_user_cannot_use_the_api(
    async_client: AsyncClient, dave_disabled_user: User
) -> None:
    """Test a disabled user is rejected even when authenticated."""
    async_client.login(dave_disabled_user)
    response = await async_client.get(ME_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
