"""The auth package enums."""

from enum import StrEnum


class TokenPurpose(StrEnum):
    """What a single-use token sent by email allows."""

    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"  # noqa: S105  # nosec B105
