"""The cli package purge command."""

import typer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.services import AuthService
from app.cli.utils import run_with_session
from app.ratelimit.services import PostgresRateLimiter


async def execute_purge(session: AsyncSession) -> tuple[int, int]:
    """Delete the expired refresh tokens and rate limit counters."""
    return (
        await AuthService.purge_expired_tokens(session),
        await PostgresRateLimiter.purge_expired(session),
    )


def purge() -> None:  # pragma: no cover
    """Delete expired refresh tokens and rate limit counters (run it daily)."""
    tokens, counters = run_with_session(execute_purge)
    typer.secho(
        f"Deleted {tokens} expired refresh tokens "
        f"and {counters} expired rate limit counters.",
        fg=typer.colors.GREEN,
    )
