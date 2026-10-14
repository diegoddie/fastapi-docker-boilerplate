"""The cli package utils."""

import asyncio
from collections.abc import Awaitable, Callable

import typer
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import session_manager


def run_with_session[T](
    function: Callable[[AsyncSession], Awaitable[T]],
) -> T:  # pragma: no cover
    """Run a coroutine function with a session on the configured database."""

    async def run() -> T:
        """Run the function, then dispose the engine while its event loop is open."""
        try:
            async with session_manager.aget_session() as session:
                return await function(session)
        finally:
            await session_manager.aclose()

    return asyncio.run(run())


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
