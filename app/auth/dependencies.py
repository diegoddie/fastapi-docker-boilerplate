"""The auth package dependencies."""

from collections.abc import Awaitable, Callable, Iterable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.auth.security import AccessTokenCodecDep, InvalidAccessTokenError
from app.core.config import settings
from app.core.database import AsyncDBSession
from app.core.exceptions import ForbiddenHTTPException, UnauthorizedHTTPException
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
