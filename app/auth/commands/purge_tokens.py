"""The auth package purge-tokens command."""

import typer

from app.auth.services import AuthService
from app.cli.utils import run_with_session


def purge_tokens() -> None:  # pragma: no cover
    """Delete the expired refresh tokens (schedule it, e.g. once a day)."""
    count = run_with_session(AuthService.purge_expired_tokens)
    typer.secho(f"Deleted {count} expired refresh tokens.", fg=typer.colors.GREEN)
