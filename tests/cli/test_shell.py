"""The cli package shell command tests."""

import pytest
from inline_snapshot import snapshot
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from app.cli.main import cli
from app.cli.shell import close_shell_session, get_shell_namespace
from app.users.models import User


def test_shell_help() -> None:
    """Test the shell command is registered in the management CLI."""
    result = CliRunner().invoke(cli, ["shell", "--help"])
    assert result.exit_code == 0
    assert "Open an IPython shell" in result.output


def test_get_shell_namespace() -> None:
    """Test the shell starts with the settings, the database and every model."""
    namespace = get_shell_namespace()
    assert list(namespace) == snapshot(
        [
            "settings",
            "session_manager",
            "session",
            "select",
            "col",
            "ExternalIdentity",
            "RateLimitCounter",
            "RefreshToken",
            "Todo",
            "User",
        ]
    )
    assert namespace["User"] is User


@pytest.mark.asyncio(loop_scope="function")
async def test_close_shell_session(mocker: MockerFixture) -> None:
    """Test leaving the shell closes its session and the database connections."""
    session = mocker.AsyncMock()
    aclose = mocker.patch("app.cli.shell.session_manager.aclose")
    await close_shell_session(session)
    session.close.assert_awaited_once()
    aclose.assert_awaited_once()
