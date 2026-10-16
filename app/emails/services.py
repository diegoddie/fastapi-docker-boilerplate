"""The emails package services."""

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage as MIMEMessage
from typing import Literal, Protocol

import structlog
from anyio import to_thread
from fastapi import BackgroundTasks

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    """A plain text email to one recipient."""

    to: str
    subject: str
    text: str


class EmailSender(Protocol):
    """Send emails."""

    async def send(self, message: EmailMessage) -> None:
        """Send an email."""
        ...  # pragma: no cover


class ConsoleEmailSender:
    """
    Write emails to the logs instead of sending them, for local development.

    Why: the links in the emails carry secret tokens, so this sender must never
    be used where the logs are kept or shipped elsewhere.
    """

    async def send(self, message: EmailMessage) -> None:
        """Log an email."""
        logger.info("email", to=message.to, subject=message.subject, text=message.text)


class SMTPEmailSender:
    """Send emails through an SMTP server (any provider: SES, Postmark, Mailgun…)."""

    def __init__(
        self,
        host: str,
        port: int,
        security: Literal["starttls", "ssl", "none"],
        username: str | None,
        password: str | None,
        sender: str,
        timeout: float,
    ) -> None:
        """Initialize the instance."""
        self.host = host
        self.port = port
        self.security = security
        self.username = username
        self.password = password
        self.sender = sender
        self.timeout = timeout

    async def send(self, message: EmailMessage) -> None:
        """Send an email."""
        # Why: smtplib is blocking, so it runs in a worker thread.
        await to_thread.run_sync(self._send, message)

    def _send(self, message: EmailMessage) -> None:
        """Send an email, blocking until the server accepts it."""
        email = MIMEMessage()
        email["From"] = self.sender
        email["To"] = message.to
        email["Subject"] = message.subject
        email.set_content(message.text)
        context = ssl.create_default_context()
        smtp = (
            smtplib.SMTP_SSL(
                self.host, self.port, timeout=self.timeout, context=context
            )
            if self.security == "ssl"
            else smtplib.SMTP(self.host, self.port, timeout=self.timeout)
        )
        with smtp:
            if self.security == "starttls":
                smtp.starttls(context=context)
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(email)


class BackgroundEmailSender:
    """Send emails after the response, so requests never wait for the server."""

    def __init__(self, sender: EmailSender, background_tasks: BackgroundTasks) -> None:
        """Initialize the instance."""
        self.sender = sender
        self.background_tasks = background_tasks

    async def send(self, message: EmailMessage) -> None:
        """Schedule an email, to be sent once the response is out."""
        self.background_tasks.add_task(self._deliver, message)

    async def _deliver(self, message: EmailMessage) -> None:
        """Send an email, logging a failure instead of raising it."""
        try:
            await self.sender.send(message)
        except Exception:
            # Why: the response is already sent, so the failure can only be
            # logged: without the recipient or the text (personal data, links).
            logger.exception("email_not_sent", subject=message.subject)
