"""The cli package purge command tests."""

from datetime import datetime, timedelta

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from time_machine import TimeMachineFixture
from typer.testing import CliRunner

from app.cli.main import cli
from app.cli.purge import execute_purge
from app.ratelimit.services import PostgresRateLimiter, RateLimit
from app.users.models import User
from tests.factories.auth import OneTimeTokenFactory, RefreshTokenFactory


def test_purge_help() -> None:
    """Test the purge command is registered in the management CLI."""
    result = CliRunner().invoke(cli, ["purge", "--help"])
    assert result.exit_code == 0
    assert "Delete expired tokens and rate limit counters" in result.output


@pytest.mark.asyncio(loop_scope="function")
async def test_execute_purge(
    async_db_session: AsyncSession,
    refresh_token_factory: type[RefreshTokenFactory],
    one_time_token_factory: type[OneTimeTokenFactory],
    bob_member_user: User,
    start_of_minute: datetime,
    time_machine: TimeMachineFixture,
) -> None:
    """Test the expired tokens and counters are deleted together."""
    for factory in (refresh_token_factory, one_time_token_factory):
        await factory.create_async(
            user_id=bob_member_user.id,
            datetime_expires=start_of_minute + timedelta(seconds=30),
        )
        # Still valid after the purge.
        await factory.create_async(user_id=bob_member_user.id)
    await PostgresRateLimiter(async_db_session).hit(
        RateLimit("search", 5, timedelta(minutes=1)), "203.0.113.7"
    )
    nothing = await execute_purge(async_db_session)
    time_machine.shift(timedelta(minutes=1))
    expired = await execute_purge(async_db_session)
    assert (nothing.pop("refresh tokens"), expired.pop("refresh tokens")) == (0, 1)
    assert (nothing.pop("single-use tokens"), expired.pop("single-use tokens")) == (
        0,
        1,
    )
    assert (nothing.pop("rate limit counters"), expired.pop("rate limit counters")) == (
        0,
        1,
    )
    # copier:payments:start
    assert (nothing.pop("webhook events"), expired.pop("webhook events")) == (0, 0)
    # copier:payments:end
    assert nothing == expired == {}
