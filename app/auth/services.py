"""The auth package services."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid7

from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlmodel import col, delete, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.emails import email_verification_message, password_reset_message
from app.auth.enums import TokenPurpose
from app.auth.identity import (
    ExternalIdentityClaims,
    IdentityProvider,
    IdentityProviderUnavailableError,
    InvalidIdentityTokenError,
)
from app.auth.models import ExternalIdentity, OneTimeToken, RefreshToken
from app.auth.schemas import TokenPublicSchemaResponse
from app.auth.security import AccessTokenCodec, PasswordHasher
from app.core.config import settings
from app.core.exceptions import (
    BadRequestHTTPException,
    ConflictHTTPException,
    ForbiddenHTTPException,
    ServiceUnavailableHTTPException,
    UnauthorizedHTTPException,
)
from app.emails.services import EmailSender
from app.users.models import User


def hash_token(token: str) -> str:
    """Return the SHA-256 hash under which a token is stored."""
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
        # Why: ends the read transaction, so the connection goes back to the pool
        # while the request waits its turn for the password hash (slow, capped).
        await session.commit()
        if user is None or user.password_hash is None:
            # Why: hash anyway, so the response time does not reveal which emails
            # are registered.
            await hasher.hash(password)
            raise UnauthorizedHTTPException(
                message="Invalid email or password.", error_code="INVALID_CREDENTIALS"
            )
        if not await hasher.verify(password, user.password_hash) or not user.is_active:
            raise UnauthorizedHTTPException(
                message="Invalid email or password.", error_code="INVALID_CREDENTIALS"
            )
        return user

    @staticmethod
    async def authenticate_external(
        token: str, provider: IdentityProvider, session: AsyncSession
    ) -> User:
        """
        Return the user of an external account, creating it on the first sign-in.

        An external account is never linked automatically to the user with the
        same email: the user links it with ``link_external``.
        """
        claims = await AuthService._verify_external_token(token, provider)
        identity = await AuthService._get_external_identity(claims, session)
        if identity is None:
            user = await AuthService._create_external_user(claims, session)
        else:
            user = identity.user
        if not user.is_active:
            raise UnauthorizedHTTPException(
                message="Invalid email or password.", error_code="INVALID_CREDENTIALS"
            )
        return user

    @staticmethod
    async def link_external(
        token: str,
        password: str,
        user: User,
        provider: IdentityProvider,
        session: AsyncSession,
        hasher: PasswordHasher,
    ) -> None:
        """Link an external account to a user, who confirms with their password."""
        # Why: an account nobody proved to own (someone else may have registered
        # the address) must not collect more ways in.
        if not user.is_email_verified:
            raise ForbiddenHTTPException(
                message="Verify your email address before linking an account.",
                error_code="EMAIL_NOT_VERIFIED",
            )
        # Why: linking adds a way to sign in, so a stolen access token alone must
        # not be enough to keep a door open into the account.
        if user.password_hash is None or not await hasher.verify(
            password, user.password_hash
        ):
            raise ForbiddenHTTPException(
                message="The password is not correct.", error_code="INVALID_PASSWORD"
            )
        claims = await AuthService._verify_external_token(token, provider)
        identity = await AuthService._get_external_identity(claims, session)
        if identity is None:
            session.add(
                ExternalIdentity(
                    user_id=user.id, provider=claims.provider, subject=claims.subject
                )
            )
            await session.commit()
        elif identity.user_id != user.id:
            raise ConflictHTTPException(
                message="The external account is linked to another user.",
                error_code="EXTERNAL_ACCOUNT_IN_USE",
            )

    @staticmethod
    async def request_email_verification(
        user: User, session: AsyncSession, sender: EmailSender
    ) -> None:
        """Email a link to verify the address, unless it is already verified."""
        if user.is_email_verified:
            return
        token = await AuthService._issue_one_time_token(
            user,
            TokenPurpose.VERIFY_EMAIL,
            timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS),
            session,
        )
        await sender.send(email_verification_message(user, token))

    @staticmethod
    async def verify_email(token: str, session: AsyncSession) -> None:
        """Mark the address of the token's user as verified."""
        user = await AuthService._consume_one_time_token(
            token, TokenPurpose.VERIFY_EMAIL, session
        )
        user.datetime_email_verified = datetime.now(UTC)
        session.add(user)
        await session.commit()

    @staticmethod
    async def request_password_reset(
        email: str, session: AsyncSession, sender: EmailSender
    ) -> None:
        """Email a link to choose a new password, if an active user has the email."""
        user = (
            await session.exec(select(User).where(User.email == email.lower()))
        ).one_or_none()
        # Why: the caller answers the same either way, so nobody learns which
        # emails are registered.
        if user is None or not user.is_active:
            return
        token = await AuthService._issue_one_time_token(
            user,
            TokenPurpose.RESET_PASSWORD,
            timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
            session,
        )
        await sender.send(password_reset_message(user, token))

    @staticmethod
    async def reset_password(
        token: str, password: str, session: AsyncSession, hasher: PasswordHasher
    ) -> None:
        """Set a new password and end every session of the token's user."""
        user = await AuthService._consume_one_time_token(
            token, TokenPurpose.RESET_PASSWORD, session
        )
        # Why: the token is used up before the slow hash, which must not run
        # while a transaction holds a connection.
        await session.commit()
        password_hash = await hasher.hash(password)
        now = datetime.now(UTC)
        if user.is_email_verified:
            await AuthService._revoke(
                col(RefreshToken.user_id) == user.id, session, now
            )
        else:
            # Why: opening the link proves, for the first time, who owns the
            # address: whatever was set up before is not trusted.
            await AuthService._take_over(user, session, now)
        user.password_hash = password_hash
        session.add(user)
        await session.commit()

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
                token_hash=hash_token(refresh_token),
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
                .where(RefreshToken.token_hash == hash_token(refresh_token))
                .options(
                    selectinload(cast(InstrumentedAttribute[User], RefreshToken.user))
                )
                .with_for_update()
            )
        ).one_or_none()
        if token is None:
            raise AuthService._invalid_refresh_token()
        revoked = token.datetime_revoked
        if revoked is not None and not await AuthService._is_concurrent_refresh(
            token.family_id, revoked, session, now
        ):
            # Why: a revoked token presented again was stolen or replayed: end the
            # whole session (family), so the copy held by the attacker dies too.
            await AuthService._revoke(
                col(RefreshToken.family_id) == token.family_id, session, now
            )
            await session.commit()
            raise AuthService._invalid_refresh_token()
        if token.datetime_expires <= now or not token.user.is_active:
            raise AuthService._invalid_refresh_token()
        if revoked is None:
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
                    RefreshToken.token_hash == hash_token(refresh_token)
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
    async def purge_expired_tokens(session: AsyncSession) -> int:
        """Delete the expired refresh tokens, returning how many were deleted."""
        # Why: a revoked token is kept until it expires, because presenting it
        # again is how a stolen token is detected.
        result = await session.exec(
            delete(RefreshToken).where(
                col(RefreshToken.datetime_expires) <= datetime.now(UTC)
            )
        )
        await session.commit()
        return result.rowcount

    @staticmethod
    async def purge_expired_one_time_tokens(session: AsyncSession) -> int:
        """Delete the expired single-use tokens, returning how many were deleted."""
        result = await session.exec(
            delete(OneTimeToken).where(
                col(OneTimeToken.datetime_expires) <= datetime.now(UTC)
            )
        )
        await session.commit()
        return result.rowcount

    @staticmethod
    async def _issue_one_time_token(
        user: User, purpose: TokenPurpose, lifetime: timedelta, session: AsyncSession
    ) -> str:
        """Return a new single-use token, replacing the user's previous ones."""
        await session.exec(
            delete(OneTimeToken).where(
                col(OneTimeToken.user_id) == user.id,
                col(OneTimeToken.purpose) == purpose,
            )
        )
        token = secrets.token_urlsafe(32)
        session.add(
            OneTimeToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=hash_token(token),
                datetime_expires=datetime.now(UTC) + lifetime,
            )
        )
        await session.commit()
        return token

    @staticmethod
    async def _consume_one_time_token(
        token: str, purpose: TokenPurpose, session: AsyncSession
    ) -> User:
        """Delete a valid single-use token and return its user (the caller commits)."""
        one_time_token = (
            await session.exec(
                select(OneTimeToken)
                .where(
                    OneTimeToken.token_hash == hash_token(token),
                    OneTimeToken.purpose == purpose,
                )
                .options(
                    selectinload(cast(InstrumentedAttribute[User], OneTimeToken.user))
                )
                .with_for_update()
            )
        ).one_or_none()
        if (
            one_time_token is None
            or one_time_token.datetime_expires <= datetime.now(UTC)
            or not one_time_token.user.is_active
        ):
            raise BadRequestHTTPException(
                message="Invalid or expired token.", error_code="INVALID_TOKEN"
            )
        await session.delete(one_time_token)
        return one_time_token.user

    @staticmethod
    async def _take_over(user: User, session: AsyncSession, now: datetime) -> None:
        """
        Hand an unverified account to whoever just proved they own the address.

        Why: whoever registered the address before may not own it, so every way
        in they could have set up ends: sessions and linked external accounts.
        The caller replaces or removes the password.
        """
        await AuthService._revoke(col(RefreshToken.user_id) == user.id, session, now)
        await session.exec(
            delete(ExternalIdentity).where(col(ExternalIdentity.user_id) == user.id)
        )
        user.datetime_email_verified = now

    @staticmethod
    async def _verify_external_token(
        token: str, provider: IdentityProvider
    ) -> ExternalIdentityClaims:
        """Return the identity asserted by an external token."""
        try:
            return await provider.verify(token)
        except IdentityProviderUnavailableError as e:
            raise ServiceUnavailableHTTPException(
                message="The identity provider is not reachable.",
                error_code="IDENTITY_PROVIDER_UNAVAILABLE",
            ) from e
        except InvalidIdentityTokenError as e:
            raise UnauthorizedHTTPException(
                message="Invalid identity token.", error_code="INVALID_ID_TOKEN"
            ) from e

    @staticmethod
    async def _get_external_identity(
        claims: ExternalIdentityClaims, session: AsyncSession
    ) -> ExternalIdentity | None:
        """Return the link to the external account, with its user, if any."""
        return (
            await session.exec(
                select(ExternalIdentity)
                .where(
                    ExternalIdentity.provider == claims.provider,
                    ExternalIdentity.subject == claims.subject,
                )
                .options(
                    selectinload(
                        cast(InstrumentedAttribute[User], ExternalIdentity.user)
                    )
                )
            )
        ).one_or_none()

    @staticmethod
    async def _create_external_user(
        claims: ExternalIdentityClaims, session: AsyncSession
    ) -> User:
        """Return the user for an external account signing in for the first time."""
        # Why: without a verified email anyone could claim someone else's address.
        if not claims.email_verified:
            raise UnauthorizedHTTPException(
                message="The email of the external account is not verified.",
                error_code="EMAIL_NOT_VERIFIED",
            )
        now = datetime.now(UTC)
        email = claims.email.lower()
        user = (
            await session.exec(select(User).where(User.email == email))
        ).one_or_none()
        if user is None:
            user = User(
                email=email,
                first_name=claims.first_name,
                last_name=claims.last_name,
                datetime_email_verified=now if claims.email_authoritative else None,
            )
        elif (
            claims.email_authoritative and not user.is_email_verified and user.is_active
        ):
            # Why: nobody proved they own this address, and the provider is
            # authoritative for it: the account belongs to the person signing in.
            await AuthService._take_over(user, session, now)
            user.password_hash = None
        else:
            # Why: an external account with this email does not prove it belongs
            # to the owner of this account: someone else may have registered the
            # address with a password, or the address may have changed hands.
            raise ConflictHTTPException(
                message=(
                    "An account with this email already exists: sign in with its "
                    "password, then link this account."
                ),
                error_code="ACCOUNT_EXISTS",
            )
        session.add(user)
        session.add(
            ExternalIdentity(
                user_id=user.id, provider=claims.provider, subject=claims.subject
            )
        )
        await session.commit()
        return user

    @staticmethod
    async def _is_concurrent_refresh(
        family_id: UUID,
        datetime_revoked: datetime,
        session: AsyncSession,
        now: datetime,
    ) -> bool:
        """
        Tell if a revoked token was rotated moments ago, in a session still open.

        Why: two tabs, or two requests sent together when the access token
        expires, present the same refresh token; the second is not a replay, and
        ending the session would log the user out. Within the grace period it
        gets a pair of its own, unless the session has ended (logout, theft).
        """
        grace = timedelta(seconds=settings.REFRESH_TOKEN_REUSE_GRACE_SECONDS)
        if now - datetime_revoked > grace:
            return False
        active = await session.exec(
            select(RefreshToken.id)
            .where(
                col(RefreshToken.family_id) == family_id,
                col(RefreshToken.datetime_revoked).is_(None),
            )
            .limit(1)
        )
        return active.first() is not None

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
