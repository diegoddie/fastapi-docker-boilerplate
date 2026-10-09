"""The auth package services."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid7

from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlmodel import col, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import RefreshToken
from app.auth.schemas import TokenPublicSchemaResponse
from app.auth.security import AccessTokenCodec, PasswordHasher
from app.core.config import settings
from app.core.exceptions import UnauthorizedHTTPException
from app.users.models import User


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hash under which a refresh token is stored."""
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """The auth service."""

    @staticmethod
    async def authenticate(
        email: str, password: str, session: AsyncSession, hasher: PasswordHasher
    ) -> User:
        """Return the active user with these credentials."""
        user = (
            await session.exec(select(User).where(User.email == email.lower()))
        ).one_or_none()
        if user is None or user.password_hash is None:
            # Why: hash anyway, so the response time does not reveal which emails
            # are registered.
            hasher.hash(password)
            raise UnauthorizedHTTPException(
                message="Invalid email or password.", error_code="INVALID_CREDENTIALS"
            )
        if not hasher.verify(password, user.password_hash) or not user.is_active:
            raise UnauthorizedHTTPException(
                message="Invalid email or password.", error_code="INVALID_CREDENTIALS"
            )
        return user

    @staticmethod
    async def issue_tokens(
        user: User,
        session: AsyncSession,
        codec: AccessTokenCodec,
        family_id: UUID | None = None,
    ) -> TokenPublicSchemaResponse:
        """Issue an access token and a refresh token (a new family if none given)."""
        refresh_token = secrets.token_urlsafe(32)
        session.add(
            RefreshToken(
                user_id=user.id,
                family_id=family_id or uuid7(),
                token_hash=hash_refresh_token(refresh_token),
                datetime_expires=datetime.now(UTC)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        await session.commit()
        access_token = codec.encode(user.id)
        return TokenPublicSchemaResponse(
            access_token=access_token.token,
            expires_in=access_token.expires_in,
            refresh_token=refresh_token,
        )

    @staticmethod
    async def refresh(
        refresh_token: str, session: AsyncSession, codec: AccessTokenCodec
    ) -> TokenPublicSchemaResponse:
        """Rotate a refresh token: revoke it and issue a new pair in its family."""
        now = datetime.now(UTC)
        token = (
            await session.exec(
                select(RefreshToken)
                .where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
                .options(
                    selectinload(cast(InstrumentedAttribute[User], RefreshToken.user))
                )
                .with_for_update()
            )
        ).one_or_none()
        if token is None:
            raise AuthService._invalid_refresh_token()
        if token.datetime_revoked is not None:
            # Why: a revoked token presented again was stolen or replayed: end the
            # whole session (family), so the copy held by the attacker dies too.
            await AuthService._revoke(
                col(RefreshToken.family_id) == token.family_id, session, now
            )
            await session.commit()
            raise AuthService._invalid_refresh_token()
        if token.datetime_expires <= now or not token.user.is_active:
            raise AuthService._invalid_refresh_token()
        token.datetime_revoked = now
        session.add(token)
        return await AuthService.issue_tokens(
            token.user, session, codec, family_id=token.family_id
        )

    @staticmethod
    async def logout(refresh_token: str, session: AsyncSession) -> None:
        """End the session the refresh token belongs to (idempotent)."""
        token = (
            await session.exec(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(refresh_token)
                )
            )
        ).one_or_none()
        if token is not None:
            await AuthService._revoke(
                col(RefreshToken.family_id) == token.family_id,
                session,
                datetime.now(UTC),
            )
            await session.commit()

    @staticmethod
    async def revoke_user_tokens(user_id: UUID, session: AsyncSession) -> None:
        """Revoke every refresh token of a user (the caller commits)."""
        await AuthService._revoke(
            col(RefreshToken.user_id) == user_id, session, datetime.now(UTC)
        )

    @staticmethod
    async def _revoke(
        condition: ColumnElement[bool], session: AsyncSession, now: datetime
    ) -> None:
        """Revoke the not yet revoked refresh tokens matching a condition."""
        await session.exec(
            update(RefreshToken)
            .where(condition, col(RefreshToken.datetime_revoked).is_(None))
            .values(datetime_revoked=now)
        )

    @staticmethod
    def _invalid_refresh_token() -> UnauthorizedHTTPException:
        """Return the error for any unusable refresh token."""
        # Why: one error for every case, so callers can't tell a revoked token
        # from an unknown one.
        return UnauthorizedHTTPException(
            message="Invalid or expired refresh token.",
            error_code="INVALID_REFRESH_TOKEN",
        )
