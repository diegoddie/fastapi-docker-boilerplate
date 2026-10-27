"""The cli package purge command."""

import typer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.services import AuthService
from app.core.database import run_with_session
from app.payments.services import PaymentService  # copier:payments
from app.ratelimit.services import PostgresRateLimiter


async def execute_purge(session: AsyncSession) -> dict[str, int]:
    """Delete the expired data, returning how many rows of each kind went."""
    return {
        "refresh tokens": await AuthService.purge_expired_tokens(session),
        "single-use tokens": await AuthService.purge_expired_one_time_tokens(session),
        "rate limit counters": await PostgresRateLimiter.purge_expired(session),
        # copier:payments:start
        "webhook events": await PaymentService.purge_webhook_events(session),
        # copier:payments:end
    }


def purge() -> None:  # pragma: no cover
    """Delete expired tokens and rate limit counters (run it daily)."""
    for kind, count in run_with_session(execute_purge).items():
        typer.secho(f"Deleted {count} expired {kind}.", fg=typer.colors.GREEN)
