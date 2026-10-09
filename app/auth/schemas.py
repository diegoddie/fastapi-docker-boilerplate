"""
The auth package schemas.

Why: unlike the rest of the API these schemas are snake_case, because the token
endpoints follow the OAuth 2.0 specification (RFC 6749), which Swagger UI's
"Authorize" button and the OAuth client libraries rely on.
"""

from typing import Literal

from pydantic import BaseModel


class TokenPublicSchemaResponse(BaseModel):
    """The token public schema response (RFC 6749, section 5.1)."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  # not a password
    expires_in: int
    refresh_token: str


class RefreshTokenPublicSchemaPayload(BaseModel):
    """The refresh token public schema payload, to refresh or log out."""

    refresh_token: str
