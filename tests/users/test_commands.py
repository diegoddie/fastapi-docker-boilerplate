"""The users package commands tests."""

from typer.testing import CliRunner

from app.cli.main import cli


def test_createsuperuser_help() -> None:
    """Test the createsuperuser command is registered in the management CLI."""
    result = CliRunner().invoke(cli, ["users", "createsuperuser", "--help"])
    assert result.exit_code == 0
    assert "Create an administrator" in result.output
