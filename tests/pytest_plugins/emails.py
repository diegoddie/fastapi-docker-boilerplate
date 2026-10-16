"""
The emails fixtures.

No test ever sends an email: every test writes them to the logs (the console
backend), and ``email_outbox`` collects the emails a test needs to read (sent
after each response, as in production).
"""

import pytest
from fastapi import FastAPI

from app.core.config import settings
from app.emails.dependencies import get_email_transport
from app.emails.services import EmailMessage


class FakeEmailSender:
    """Collect the emails instead of sending them."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self.outbox: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        """Collect an email."""
        self.outbox.append(message)


@pytest.fixture(autouse=True)
def no_email_delivery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never deliver an email from a test, whatever the environment."""
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "console")


@pytest.fixture
def email_outbox(test_app: FastAPI) -> list[EmailMessage]:
    """Return the emails sent by the application, which are never delivered."""
    sender = FakeEmailSender()
    test_app.dependency_overrides[get_email_transport] = lambda: sender
    return sender.outbox
