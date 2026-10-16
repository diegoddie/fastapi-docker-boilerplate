"""The emails package dependencies tests."""

from fastapi import BackgroundTasks
from pydantic import SecretStr
from pytest_mock import MockerFixture

from app.core.config import settings
from app.emails.dependencies import get_email_sender, get_email_transport
from app.emails.services import (
    BackgroundEmailSender,
    ConsoleEmailSender,
    SMTPEmailSender,
)


def test_get_email_transport_console(mocker: MockerFixture) -> None:
    """Test the console backend writes the emails to the logs."""
    mocker.patch.object(settings, "EMAIL_BACKEND", "console")
    assert isinstance(get_email_transport(), ConsoleEmailSender)


def test_get_email_transport_smtp(mocker: MockerFixture) -> None:
    """Test the SMTP backend is configured from the settings."""
    mocker.patch.object(settings, "EMAIL_BACKEND", "smtp")
    mocker.patch.object(settings, "SMTP_USERNAME", "mailer")
    for password, expected in ((SecretStr("secret"), "secret"), (None, None)):
        mocker.patch.object(settings, "SMTP_PASSWORD", password)
        transport = get_email_transport()
        assert isinstance(transport, SMTPEmailSender)
        assert (transport.host, transport.username, transport.password) == (
            settings.SMTP_HOST,
            "mailer",
            expected,
        )


def test_get_email_sender() -> None:
    """Test requests send their emails after the response."""
    transport = ConsoleEmailSender()
    sender = get_email_sender(BackgroundTasks(), transport)
    assert isinstance(sender, BackgroundEmailSender)
    assert sender.sender is transport
