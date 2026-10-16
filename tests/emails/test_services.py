"""The emails package services tests."""

from collections.abc import Callable
from typing import Any, Literal

import pytest
from fastapi import BackgroundTasks
from pytest_mock import MockerFixture

from app.emails.services import (
    BackgroundEmailSender,
    ConsoleEmailSender,
    EmailMessage,
    SMTPEmailSender,
)
from tests.pytest_plugins.emails import FakeEmailSender


@pytest.fixture
def welcome_email() -> EmailMessage:
    """Return an email to send."""
    return EmailMessage(to="bob@example.com", subject="Welcome", text="Hi Bob")


@pytest.mark.asyncio(loop_scope="function")
async def test_console_email_sender(
    welcome_email: EmailMessage,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test emails are written to the logs instead of being sent."""
    await ConsoleEmailSender().send(welcome_email)
    (event,) = log_events("email")
    assert (event["to"], event["subject"], event["text"]) == (
        "bob@example.com",
        "Welcome",
        "Hi Bob",
    )


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize(
    ("security", "smtp_class", "starttls"),
    [("starttls", "SMTP", True), ("ssl", "SMTP_SSL", False), ("none", "SMTP", False)],
)
async def test_smtp_email_sender(
    mocker: MockerFixture,
    welcome_email: EmailMessage,
    security: Literal["starttls", "ssl", "none"],
    smtp_class: str,
    starttls: bool,
) -> None:
    """Test emails are sent through the SMTP server, with the chosen security."""
    smtp = mocker.patch(f"app.emails.services.smtplib.{smtp_class}")
    server = smtp.return_value
    sender = SMTPEmailSender(
        host="smtp.example.com",
        port=587,
        security=security,
        username="mailer",
        password="secret",
        sender="no-reply@example.com",
        timeout=5,
    )
    await sender.send(welcome_email)
    assert smtp.call_args.args == ("smtp.example.com", 587)
    assert server.starttls.called is starttls
    server.login.assert_called_once_with("mailer", "secret")
    (sent,), _ = server.send_message.call_args
    assert (sent["From"], sent["To"], sent["Subject"]) == (
        "no-reply@example.com",
        "bob@example.com",
        "Welcome",
    )
    assert sent.get_content() == "Hi Bob\n"


@pytest.mark.asyncio(loop_scope="function")
async def test_smtp_email_sender_without_login(
    mocker: MockerFixture, welcome_email: EmailMessage
) -> None:
    """Test a server without authentication gets no login."""
    smtp = mocker.patch("app.emails.services.smtplib.SMTP")
    sender = SMTPEmailSender(
        host="localhost",
        port=25,
        security="none",
        username=None,
        password=None,
        sender="no-reply@example.com",
        timeout=5,
    )
    await sender.send(welcome_email)
    server = smtp.return_value
    server.login.assert_not_called()
    server.send_message.assert_called_once()


@pytest.mark.asyncio(loop_scope="function")
async def test_background_email_sender(welcome_email: EmailMessage) -> None:
    """Test an email leaves only when the background tasks run."""
    transport, background_tasks = FakeEmailSender(), BackgroundTasks()
    await BackgroundEmailSender(transport, background_tasks).send(welcome_email)
    assert transport.outbox == []
    await background_tasks()
    assert transport.outbox == [welcome_email]


@pytest.mark.asyncio(loop_scope="function")
async def test_background_email_sender_failure(
    mocker: MockerFixture,
    welcome_email: EmailMessage,
    log_events: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Test a failed delivery is logged without the recipient or the text."""
    transport = mocker.AsyncMock()
    transport.send.side_effect = ConnectionRefusedError()
    background_tasks = BackgroundTasks()
    await BackgroundEmailSender(transport, background_tasks).send(welcome_email)
    await background_tasks()
    (event,) = log_events("email_not_sent")
    assert event["subject"] == "Welcome"
    assert "bob@example.com" not in str(event)
