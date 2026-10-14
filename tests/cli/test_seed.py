"""The cli package seed command tests."""

import pytest
from inline_snapshot import snapshot
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typer.testing import CliRunner

from app.cli.main import cli
from app.cli.seed import execute_seed
from app.todos.models import Todo
from app.users.models import User
from tests.factories.users import TEST_PASSWORD
from tests.utils import AsyncClient


def test_seed_help() -> None:
    """Test the seed command is registered in the management CLI."""
    result = CliRunner().invoke(cli, ["seed", "--help"])
    assert result.exit_code == 0
    assert "Fill the local database" in result.output


@pytest.mark.asyncio(loop_scope="function")
async def test_execute_seed(
    async_db_session: AsyncSession, async_client: AsyncClient
) -> None:
    """Test the seed creates a user per group, each with the demo todos."""
    users = await execute_seed(TEST_PASSWORD, async_db_session)
    async_db_session.expunge_all()
    assert [(user.email, user.groups) for user in users] == snapshot(
        [
            ("alice@example.com", ["admin"]),
            ("bob@example.com", ["member"]),
            ("carol@example.com", ["viewer"]),
        ]
    )
    todos = (
        await async_db_session.exec(
            select(Todo)
            .where(col(Todo.owner_id) == users[1].id)
            .order_by(col(Todo.title))
        )
    ).all()
    assert [
        (
            todo.title,
            todo.status,
            todo.priority,
            todo.due_date and (todo.due_date - todo.datetime_created.date()).days,
        )
        for todo in todos
    ] == snapshot(
        [
            ("Book the summer holidays", "todo", "medium", 14),
            ("Prepare the quarterly report", "in_progress", "high", 2),
            ("Read the architecture docs", "done", "medium", None),
            ("Renew the passport", "todo", "high", -3),
            ("Water the plants", "todo", "low", None),
        ]
    )
    # The demo users log in with the password given to the command.
    await async_client.password_login("carol@example.com")


@pytest.mark.asyncio(loop_scope="function")
async def test_execute_seed_existing_user(
    async_db_session: AsyncSession, alice_admin_user: User
) -> None:
    """Test the seed leaves the existing demo users untouched."""
    users = await execute_seed(TEST_PASSWORD, async_db_session)
    assert [user.email for user in users] == snapshot(
        ["bob@example.com", "carol@example.com"]
    )
    alice_todos = await async_db_session.exec(
        select(Todo).where(col(Todo.owner_id) == alice_admin_user.id)
    )
    assert alice_todos.all() == []
