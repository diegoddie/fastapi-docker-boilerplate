"""
The users fixtures.

The personas are deterministic users that every test can rely on:

- Alice is an administrator;
- Bob is a member;
- Carol is a viewer (read-only);
- Dave is a disabled member.
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest
import pytest_asyncio

from app.users.enums import Group
from app.users.models import User
from tests.factories.users import UserFactory


@pytest.fixture
def user_factory(seed_factories: None) -> type[UserFactory]:
    """Return the user factory, bound to the test database."""
    return UserFactory


@pytest_asyncio.fixture(loop_scope="function")
async def alice_admin_user(user_factory: type[UserFactory]) -> User:
    """Return Alice, an administrator."""
    return await user_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000001"),
        email="alice@example.com",
        first_name="Alice",
        last_name="Admin",
        groups=[Group.ADMIN],
    )


@pytest_asyncio.fixture(loop_scope="function")
async def bob_member_user(user_factory: type[UserFactory]) -> User:
    """Return Bob, a member."""
    return await user_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000002"),
        email="bob@example.com",
        first_name="Bob",
        last_name="Member",
        groups=[Group.MEMBER],
    )


@pytest_asyncio.fixture(loop_scope="function")
async def carol_viewer_user(user_factory: type[UserFactory]) -> User:
    """Return Carol, a viewer."""
    return await user_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000003"),
        email="carol@example.com",
        first_name="Carol",
        last_name="Viewer",
        groups=[Group.VIEWER],
    )


@pytest_asyncio.fixture(loop_scope="function")
async def dave_disabled_user(user_factory: type[UserFactory]) -> User:
    """Return Dave, a disabled member."""
    return await user_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000004"),
        email="dave@example.com",
        first_name="Dave",
        last_name="Disabled",
        groups=[Group.MEMBER],
        datetime_disabled=datetime(2026, 1, 1, tzinfo=UTC),
    )
