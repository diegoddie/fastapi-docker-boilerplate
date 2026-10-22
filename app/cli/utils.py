"""The cli package utils."""

import typer
from pydantic import ValidationError

from app.core.config import settings


def require_local_environment() -> None:
    """Stop the command unless it runs in a local environment."""
    if settings.ENVIRONMENT != "local":
        typer.secho(
            "This command runs only in local environments.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)


def echo_validation_errors(error: ValidationError) -> None:
    """Print the invalid fields of a validation error."""
    for item in error.errors():
        typer.secho(f"{item['loc'][0]}: {item['msg']}", fg=typer.colors.RED, err=True)
