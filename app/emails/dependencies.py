"""The emails package dependencies."""

from typing import Annotated

from fastapi import BackgroundTasks, Depends

from app.core.config import settings
from app.emails.services import (
    BackgroundEmailSender,
    ConsoleEmailSender,
    EmailSender,
    SMTPEmailSender,
)


def get_email_transport() -> EmailSender:
    """Return the sender delivering the emails, as the settings say."""
    if settings.email_backend == "console":
        return ConsoleEmailSender()
    return SMTPEmailSender(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        security=settings.SMTP_SECURITY,
        username=settings.SMTP_USERNAME,
        password=(
            settings.SMTP_PASSWORD.get_secret_value()
            if settings.SMTP_PASSWORD
            else None
        ),
        sender=settings.EMAIL_FROM,
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    )


def get_email_sender(
    background_tasks: BackgroundTasks,
    transport: Annotated[EmailSender, Depends(get_email_transport)],
) -> EmailSender:
    """Return the sender of the request: emails leave after the response."""
    return BackgroundEmailSender(transport, background_tasks)


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
