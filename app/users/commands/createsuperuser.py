"""The users package createsuperuser command."""

from typing import Annotated

import typer
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.auth.security import password_hasher
from app.cli.utils import echo_validation_errors, run_with_session
from app.users.enums import Group
from app.users.schemas import UserPublicSchemaCreate
from app.users.services import UserService


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
        user = run_with_session(
            lambda session: UserService.create(
                payload, session, password_hasher, groups=[Group.ADMIN]
            )
        )
    except ValidationError as e:
        echo_validation_errors(e)
        raise typer.Exit(1) from e
    except IntegrityError as e:
        typer.secho(
            f"A user with email {email} already exists.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(1) from e
    typer.secho(f"Administrator {user.email} created.", fg=typer.colors.GREEN)
