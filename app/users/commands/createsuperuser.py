"""The users package createsuperuser command."""

import asyncio
from typing import Annotated

import typer
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.auth.security import password_hasher
from app.core.database import session_manager
from app.users.enums import Group
from app.users.models import User
from app.users.schemas import UserPublicSchemaCreate
from app.users.services import UserService


async def execute_createsuperuser(
    payload: UserPublicSchemaCreate,
) -> User:  # pragma: no cover
    """Create an administrator in the database configured by the settings."""
    try:
        async with session_manager.aget_session() as session:
            return await UserService.create(
                payload, session, password_hasher, groups=[Group.ADMIN]
            )
    finally:
        await session_manager.aclose()


def createsuperuser(
    email: Annotated[str, typer.Option(prompt=True)],
    first_name: Annotated[str, typer.Option(prompt=True)],
    last_name: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[
        str, typer.Option(prompt=True, hide_input=True, confirmation_prompt=True)
    ],
) -> None:  # pragma: no cover
    """Create an administrator (e.g. the very first user)."""
    try:
        payload = UserPublicSchemaCreate(
            email=email, first_name=first_name, last_name=last_name, password=password
        )
        user = asyncio.run(execute_createsuperuser(payload))
    except ValidationError as e:
        for error in e.errors():
            typer.secho(f"{error['loc'][0]}: {error['msg']}", fg=typer.colors.RED)
        raise typer.Exit(1) from e
    except IntegrityError as e:
        typer.secho(f"A user with email {email} already exists.", fg=typer.colors.RED)
        raise typer.Exit(1) from e
    typer.secho(f"Administrator {user.email} created.", fg=typer.colors.GREEN)
