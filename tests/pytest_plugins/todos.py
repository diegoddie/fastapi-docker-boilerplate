"""
The todos fixtures.

Bob (a member) has three todos, with different status, priority and due date,
to test filters and ordering; Alice (an administrator) has one, to test that
users only reach their own todos while administrators reach them all.
"""

from datetime import date
from uuid import UUID

import pytest
import pytest_asyncio

from app.todos.enums import TodoPriority, TodoStatus
from app.todos.models import Todo
from app.users.models import User
from tests.factories.todos import TodoFactory


@pytest.fixture
def todo_factory(seed_factories: None) -> type[TodoFactory]:
    """Return the todo factory, bound to the test database."""
    return TodoFactory


@pytest_asyncio.fixture(loop_scope="function")
async def bob_milk_todo(todo_factory: type[TodoFactory], bob_member_user: User) -> Todo:
    """Return Bob's urgent todo: buy milk."""
    return await todo_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000101"),
        owner_id=bob_member_user.id,
        title="Buy milk",
        description="",
        status=TodoStatus.TODO,
        priority=TodoPriority.HIGH,
        due_date=date(2026, 10, 20),
    )


@pytest_asyncio.fixture(loop_scope="function")
async def bob_report_todo(
    todo_factory: type[TodoFactory], bob_member_user: User
) -> Todo:
    """Return Bob's todo in progress: the quarterly report."""
    return await todo_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000102"),
        owner_id=bob_member_user.id,
        title="Write the quarterly report",
        description="Numbers for Q3",
        status=TodoStatus.IN_PROGRESS,
        priority=TodoPriority.MEDIUM,
        due_date=date(2026, 10, 15),
    )


@pytest_asyncio.fixture(loop_scope="function")
async def bob_flight_todo(
    todo_factory: type[TodoFactory], bob_member_user: User
) -> Todo:
    """Return Bob's done todo, without a due date: book the flight."""
    return await todo_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000103"),
        owner_id=bob_member_user.id,
        title="Book the flight",
        description="",
        status=TodoStatus.DONE,
        priority=TodoPriority.LOW,
        due_date=None,
    )


@pytest_asyncio.fixture(loop_scope="function")
async def alice_review_todo(
    todo_factory: type[TodoFactory], alice_admin_user: User
) -> Todo:
    """Return Alice's todo: review the pull requests."""
    return await todo_factory.create_async(
        id=UUID("0194f8a0-2000-7000-8000-000000000104"),
        owner_id=alice_admin_user.id,
        title="Review pull requests",
        description="",
        status=TodoStatus.TODO,
        priority=TodoPriority.MEDIUM,
        due_date=date(2026, 10, 18),
    )
