"""The auth package commands tests."""

from typer.testing import CliRunner

from app.cli.main import cli


def test_purge_tokens_help() -> None:
    """Test the purge-tokens command is registered in the management CLI."""
    result = CliRunner().invoke(cli, ["auth", "purge-tokens", "--help"])
    assert result.exit_code == 0
    assert "Delete the expired refresh tokens" in result.output
