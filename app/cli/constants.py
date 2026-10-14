"""The cli package constants."""

from typing import NamedTuple

from app.todos.enums import TodoPriority, TodoStatus
from app.users.enums import Group


class SeedUser(NamedTuple):
    """A demo user created by the seed command."""

    email: str
    first_name: str
    last_name: str
    group: Group


class SeedTodo(NamedTuple):
    """A demo todo, created for every demo user."""

    title: str
    status: TodoStatus
    priority: TodoPriority
    description: str = ""
    # Why: relative to the day of the seed, so some todos are always overdue.
    due_in_days: int | None = None


# Why: the same personas as the tests, so the demo data reads like the test suite.
SEED_USERS = (
    SeedUser("alice@example.com", "Alice", "Admin", Group.ADMIN),
    SeedUser("bob@example.com", "Bob", "Member", Group.MEMBER),
    SeedUser("carol@example.com", "Carol", "Viewer", Group.VIEWER),
)
SEED_TODOS = (
    SeedTodo("Read the architecture docs", TodoStatus.DONE, TodoPriority.MEDIUM),
    SeedTodo(
        "Renew the passport",
        TodoStatus.TODO,
        TodoPriority.HIGH,
        description="Book an appointment and bring two photos.",
        due_in_days=-3,
    ),
    SeedTodo(
        "Prepare the quarterly report",
        TodoStatus.IN_PROGRESS,
        TodoPriority.HIGH,
        description="Revenue, costs and the hiring plan.",
        due_in_days=2,
    ),
    SeedTodo(
        "Book the summer holidays",
        TodoStatus.TODO,
        TodoPriority.MEDIUM,
        due_in_days=14,
    ),
    SeedTodo("Water the plants", TodoStatus.TODO, TodoPriority.LOW),
)
