"""The users package services tests."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import password_hasher
from app.users.enums import Group
from app.users.schemas import UserPublicSchemaCreate
from app.users.services import UserService


@pytest.mark.asyncio(loop_scope="function")
async def test_create_user_with_groups(async_db_session: AsyncSession) -> None:
    """Test users can be created with explicit groups (e.g. administrators)."""
    payload = UserPublicSchemaCreate(
        email="Root@Example.com",
        first_name="Root",
        last_name="Admin",
        password="a-strong-password",
    )
    user = await UserService.create(
        payload, async_db_session, password_hasher, groups=[Group.ADMIN]
    )
    assert user.email == "root@example.com"
    assert user.groups == [Group.ADMIN]
