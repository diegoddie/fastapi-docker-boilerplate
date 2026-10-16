"""The auth package emails."""

from app.auth.constants import RESET_PASSWORD_PATH, VERIFY_EMAIL_PATH
from app.core.config import settings
from app.emails.services import EmailMessage
from app.users.models import User


def frontend_link(path: str, token: str) -> str:
    """Return the link to a frontend page, carrying a token in the fragment."""
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}#token={token}"


def email_verification_message(user: User, token: str) -> EmailMessage:
    """Return the email asking a user to verify their address."""
    link = frontend_link(VERIFY_EMAIL_PATH, token)
    hours = settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
    return EmailMessage(
        to=user.email,
        subject="Verify your email address",
        text=(
            f"Hi {user.first_name},\n\n"
            f"open this link within {hours} hours to verify your email address:\n\n"
            f"{link}\n\n"
            "If you did not create an account, ignore this email.\n"
        ),
    )


def password_reset_message(user: User, token: str) -> EmailMessage:
    """Return the email with a link to choose a new password."""
    link = frontend_link(RESET_PASSWORD_PATH, token)
    minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    return EmailMessage(
        to=user.email,
        subject="Reset your password",
        text=(
            f"Hi {user.first_name},\n\n"
            f"open this link within {minutes} minutes to choose a new password:\n\n"
            f"{link}\n\n"
            "Choosing a new password logs you out everywhere. If you did not ask "
            "for it, ignore this email: your password does not change.\n"
        ),
    )
