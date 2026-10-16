"""The auth package dependencies."""

from collections.abc import Awaitable, Callable, Iterable
from datetime import timedelta
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.auth.constants import (
    AUTH_REQUESTS_RATE_LIMIT,
    EMAILS_RATE_LIMIT,
    PASSWORD_ATTEMPTS_RATE_LIMIT,
    REGISTRATIONS_RATE_LIMIT,
)
from app.auth.schemas import EmailPublicSchemaPayload
from app.auth.security import AccessTokenCodecDep, InvalidAccessTokenError
from app.core.config import settings
from app.core.database import AsyncDBSession
from app.core.exceptions import ForbiddenHTTPException, UnauthorizedHTTPException
from app.ratelimit.dependencies import ClientIP, RateLimiterDep
from app.ratelimit.services import RateLimit, RateLimiter
from app.users.models import User

# Why: declaring the login URL enables the "Authorize" button in Swagger UI.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_ROOT}/v1/auth/login/")


def _invalid_access_token() -> UnauthorizedHTTPException:
    """Return the error for an unusable access token."""
    return UnauthorizedHTTPException(
        message="Invalid or expired access token.",
        error_code="INVALID_TOKEN",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_token_subject(
    token: Annotated[str, Depends(oauth2_scheme)], codec: AccessTokenCodecDep
) -> UUID:
    """Return the id of the user the bearer access token was issued to."""
    try:
        return codec.decode(token)
    except InvalidAccessTokenError as e:
        raise _invalid_access_token() from e


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_token_subject)], session: AsyncDBSession
) -> User:
    """Return the authenticated user, rejecting deleted and disabled ones."""
    # Why: the user is read on every request, so disabling an account takes effect
    # immediately, even while its access tokens are still valid.
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _invalid_access_token()
    # Why: from here on, every log line of the request says who made it.
    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    return user


AuthenticatedUser = Annotated[User, Depends(get_current_user)]


def require_any_permissions(
    permissions: Iterable[str],
) -> Callable[[User], Awaitable[User]]:
    """Return a dependency that requires at least one of the permissions."""
    required = frozenset(permissions)

    async def check_any_permissions(user: AuthenticatedUser) -> User:
        """Reject users without any of the required permissions."""
        if not user.permissions & required:
            raise ForbiddenHTTPException(
                message="You do not have permission to perform this action."
            )
        return user

    return check_any_permissions


async def limit_auth_requests(ip: ClientIP, limiter: RateLimiterDep) -> None:
    """Limit the authentication requests of each IP address."""
    await limiter.hit(
        RateLimit(
            AUTH_REQUESTS_RATE_LIMIT,
            settings.RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE,
            timedelta(minutes=1),
        ),
        ip,
    )


async def limit_registrations(ip: ClientIP, limiter: RateLimiterDep) -> None:
    """Limit the registrations from each IP address."""
    await limiter.hit(
        RateLimit(
            REGISTRATIONS_RATE_LIMIT,
            settings.RATE_LIMIT_REGISTRATIONS_PER_HOUR,
            timedelta(hours=1),
        ),
        ip,
    )


async def limit_login_attempts(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    ip: ClientIP,
    limiter: RateLimiterDep,
) -> None:
    """Limit the password attempts on each account from each IP address."""
    await _limit_password_attempts(form.username, ip, limiter)


async def limit_link_attempts(
    user: AuthenticatedUser, ip: ClientIP, limiter: RateLimiterDep
) -> None:
    """Limit the password confirmations of each user from each IP address."""
    await _limit_password_attempts(user.email, ip, limiter)


async def _limit_password_attempts(email: str, ip: str, limiter: RateLimiter) -> None:
    """Count a password attempt on an account from an IP address."""
    # Why: counting per account alone would let anyone lock a user out; per
    # account and IP, guessing is slowed down and the owner can still log in.
    await limiter.hit(
        RateLimit(
            PASSWORD_ATTEMPTS_RATE_LIMIT,
            settings.RATE_LIMIT_PASSWORD_ATTEMPTS_PER_MINUTE,
            timedelta(minutes=1),
        ),
        f"{email.strip().lower()}|{ip}",
    )


async def limit_password_reset_emails(
    payload: EmailPublicSchemaPayload, limiter: RateLimiterDep
) -> None:
    """Limit the password reset emails sent to each address."""
    await _limit_emails(payload.email, limiter)


async def limit_verification_emails(
    user: AuthenticatedUser, limiter: RateLimiterDep
) -> None:
    """Limit the verification emails sent to each address."""
    await _limit_emails(user.email, limiter)


async def _limit_emails(email: str, limiter: RateLimiter) -> None:
    """Count an email sent to an address."""
    # Why: per recipient, whatever the IP, so nobody can flood someone's inbox.
    await limiter.hit(
        RateLimit(
            EMAILS_RATE_LIMIT,
            settings.RATE_LIMIT_EMAILS_PER_HOUR,
            timedelta(hours=1),
        ),
        email.strip().lower(),
    )
