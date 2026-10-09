"""The users package services."""

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.security import PasswordHasher
from app.auth.services import AuthService
from app.core.exceptions import ForbiddenHTTPException, NotFoundHTTPException
from app.users.constants import DEFAULT_GROUPS
from app.users.enums import Group
from app.users.models import User
from app.users.schemas import (
    UserMePublicSchemaUpdate,
    UserPublicSchemaCreate,
    UserPublicSchemaUpdate,
)


class UserService:
    """The user service."""

    @staticmethod
    async def get_by_id(user_id: UUID, session: AsyncSession) -> User:
        """Return a user by id."""
        if (user := await session.get(User, user_id)) is None:
            raise NotFoundHTTPException(
                message=f"User with id {user_id} not found",
                error_code="USER_NOT_FOUND",
            )
        return user

    @staticmethod
    def list_query() -> SelectOfScalar[User]:
        """Return the list users query."""
        return select(User).order_by(col(User.email), col(User.id))

    @staticmethod
    async def create(
        payload: UserPublicSchemaCreate,
        session: AsyncSession,
        hasher: PasswordHasher,
        groups: Iterable[Group] = DEFAULT_GROUPS,
    ) -> User:
        """Create a user with a password (a duplicate email is a 409)."""
        user = User.model_validate(
            payload.model_dump(exclude={"password"})
            | {"password_hash": hasher.hash(payload.password), "groups": list(groups)}
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise
        return user

    @staticmethod
    async def update_me(
        user: User, payload: UserMePublicSchemaUpdate, session: AsyncSession
    ) -> None:
        """Update the current user's own profile."""
        user.sqlmodel_update(payload.model_dump(exclude_unset=True))
        session.add(user)
        await session.commit()

    @staticmethod
    async def update(
        user_id: UUID,
        payload: UserPublicSchemaUpdate,
        session: AsyncSession,
        current_user: User,
    ) -> None:
        """Update a user as an administrator."""
        data = payload.model_dump(exclude_unset=True)
        if user_id == current_user.id and {"groups", "datetime_disabled"} & set(data):
            # Why: an administrator must not lock themselves out by mistake.
            raise ForbiddenHTTPException(
                message="You cannot change your own groups or disable yourself.",
                error_code="SELF_ACCESS_CHANGE",
            )
        user = await UserService.get_by_id(user_id, session)
        user.sqlmodel_update(data)
        session.add(user)
        if not user.is_active:
            await AuthService.revoke_user_tokens(user.id, session)
        await session.commit()

    @staticmethod
    async def disable(user_id: UUID, session: AsyncSession, current_user: User) -> None:
        """Disable (soft delete) a user and end all their sessions."""
        await UserService.update(
            user_id,
            UserPublicSchemaUpdate(datetime_disabled=datetime.now(UTC)),
            session,
            current_user,
        )
