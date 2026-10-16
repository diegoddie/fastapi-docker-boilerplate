"""
The auth package schemas.

Why: unlike the rest of the API the token schemas are snake_case, because the
token endpoints follow the OAuth 2.0 specification (RFC 6749), which Swagger
UI's "Authorize" button and the OAuth client libraries rely on.
"""

from typing import Literal

from pydantic import BaseModel, EmailStr

from app.commons.schemas import BasePublicSchema
from app.users.schemas import Password


class TokenPublicSchemaResponse(BaseModel):
    """The token public schema response (RFC 6749, section 5.1)."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  # not a password
    expires_in: int
    refresh_token: str


class RefreshTokenPublicSchemaPayload(BaseModel):
    """The refresh token public schema payload, to refresh or log out."""

    refresh_token: str


class IdTokenPublicSchemaPayload(BaseModel):
    """The ID token public schema payload, as issued by an identity provider."""

    id_token: str


class IdTokenLinkPublicSchemaPayload(IdTokenPublicSchemaPayload):
    """The payload to link an external account: its ID token and the password."""

    password: str


class EmailPublicSchemaPayload(BasePublicSchema):
    """The email public schema payload, to ask for a password reset link."""

    email: EmailStr


class OneTimeTokenPublicSchemaPayload(BasePublicSchema):
    """The single-use token public schema payload, from a link in an email."""

    token: str


class PasswordResetPublicSchemaPayload(OneTimeTokenPublicSchemaPayload):
    """The password reset public schema payload: the token and a new password."""

    password: Password
