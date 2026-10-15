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
from tests.factories.auth import RefreshTokenFactory


def test_purge_help() -> None:
    """Test the purge command is registered in the management CLI."""
    result = CliRunner().invoke(cli, ["purge", "--help"])
    assert result.exit_code == 0
    assert "Delete expired refresh tokens" in result.output


@pytest.mark.asyncio(loop_scope="function")
async def test_execute_purge(
    async_db_session: AsyncSession,
    refresh_token_factory: type[RefreshTokenFactory],
    bob_member_user: User,
    start_of_minute: datetime,
    time_machine: TimeMachineFixture,
) -> None:
    """Test the expired tokens and counters are deleted together."""
    await refresh_token_factory.create_async(
        user_id=bob_member_user.id,
        datetime_expires=start_of_minute + timedelta(seconds=30),
    )
    await PostgresRateLimiter(async_db_session).hit(
        RateLimit("search", 5, timedelta(minutes=1)), "203.0.113.7"
    )
    assert await execute_purge(async_db_session) == (0, 0)
    time_machine.shift(timedelta(minutes=1))
    assert await execute_purge(async_db_session) == (1, 1)
