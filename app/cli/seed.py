"""The cli package seed command."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import typer
from pydantic import ValidationError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import password_hasher
from app.cli.constants import SEED_TODOS, SEED_USERS
from app.cli.utils import echo_validation_errors, require_local_environment
from app.core.database import run_with_session
from app.todos.schemas import TodoPublicSchemaCreate
from app.todos.services import TodoService
from app.users.models import User
from app.users.schemas import UserPublicSchemaCreate
from app.users.services import UserService


async def execute_seed(password: str, session: AsyncSession) -> list[User]:
    """Create the demo users with their todos, skipping the users that exist."""
    today = datetime.now(UTC).date()
    created: list[User] = []
    for seed_user in SEED_USERS:
        existing = await session.exec(
            select(User).where(col(User.email) == seed_user.email)
        )
        if existing.first() is not None:
            continue
        user = await UserService.create(
            UserPublicSchemaCreate(
                email=seed_user.email,
                first_name=seed_user.first_name,
                last_name=seed_user.last_name,
                password=password,
            ),
            session,
            password_hasher,
            groups=[seed_user.group],
            email_verified=True,
        )
        for seed_todo in SEED_TODOS:
            await TodoService.create(
                TodoPublicSchemaCreate(
                    title=seed_todo.title,
                    description=seed_todo.description,
                    status=seed_todo.status,
                    priority=seed_todo.priority,
                    due_date=(
                        None
                        if seed_todo.due_in_days is None
                        else today + timedelta(days=seed_todo.due_in_days)
                    ),
                ),
                session,
                user,
            )
        created.append(user)
    return created


def seed(
    password: Annotated[
        str | None,
        typer.Option(help="The password of the demo users (asked when missing)."),
    ] = None,
) -> None:  # pragma: no cover
    """Fill the local database with demo users and todos."""
    require_local_environment()
    if password is None:
        password = typer.prompt(
            "Password of the demo users", hide_input=True, confirmation_prompt=True
        )
    try:
        users = run_with_session(lambda session: execute_seed(password, session))
    except ValidationError as e:
        echo_validation_errors(e)
        raise typer.Exit(1) from e
    if not users:
        typer.secho("The demo users already exist.", fg=typer.colors.YELLOW)
    for user in users:
        typer.secho(
            f"Created {user.email} ({', '.join(user.groups)}) "
            f"with {len(SEED_TODOS)} todos.",
            fg=typer.colors.GREEN,
        )
