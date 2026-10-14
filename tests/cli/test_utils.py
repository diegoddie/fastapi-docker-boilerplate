"""The cli package utils tests."""

import pytest
import typer
from pydantic import ValidationError
from pytest_mock import MockerFixture

from app.cli.utils import echo_validation_errors, require_local_environment
from app.core.config import settings
from app.users.schemas import UserPublicSchemaCreate


def test_require_local_environment_local(mocker: MockerFixture) -> None:
    """Test a command can run in a local environment."""
    mocker.patch.object(settings, "ENVIRONMENT", "local")
    require_local_environment()


def test_require_local_environment_remote(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test a local-only command stops in a remote environment."""
    mocker.patch.object(settings, "ENVIRONMENT", "remote")
    with pytest.raises(typer.Exit):
        require_local_environment()
    assert "only in local environments" in capsys.readouterr().err


def test_echo_validation_errors(capsys: pytest.CaptureFixture[str]) -> None:
    """Test each invalid field is printed with its error."""
    with pytest.raises(ValidationError) as exc_info:
        UserPublicSchemaCreate(
            email="not-an-email", first_name="Alice", last_name="", password="short"
        )
    echo_validation_errors(exc_info.value)
    assert capsys.readouterr().err.splitlines() == [
        "email: value is not a valid email address: "
        "An email address must have an @-sign.",
        "password: String should have at least 8 characters",
    ]
