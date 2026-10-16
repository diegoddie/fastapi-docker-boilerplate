"""The auth package router."""

import html
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import (
    AuthenticatedUser,
    limit_auth_requests,
    limit_link_attempts,
    limit_login_attempts,
    limit_password_reset_emails,
    limit_registrations,
    limit_verification_emails,
)
from app.auth.identity import GoogleIdentityProviderDep
from app.auth.schemas import (
    EmailPublicSchemaPayload,
    IdTokenLinkPublicSchemaPayload,
    IdTokenPublicSchemaPayload,
    OneTimeTokenPublicSchemaPayload,
    PasswordResetPublicSchemaPayload,
    RefreshTokenPublicSchemaPayload,
    TokenPublicSchemaResponse,
)
from app.auth.security import AccessTokenCodecDep, PasswordHasherDep
from app.auth.services import AuthService
from app.core.config import settings
from app.core.database import AsyncDBSession
from app.core.exceptions import NotFoundHTTPException
from app.emails.dependencies import EmailSenderDep
from app.users.schemas import UserPublicSchemaCreate, UserPublicSchemaResponse
from app.users.services import UserService

router = APIRouter()

GOOGLE_TEST_PAGE = Path(__file__).parent / "templates" / "google_sign_in.html"


@router.post(
    "/register/",
    summary="Register a new user",
    status_code=status.HTTP_201_CREATED,
    response_model=UserPublicSchemaResponse,
    dependencies=[Depends(limit_auth_requests), Depends(limit_registrations)],
)
async def register_user_route(
    payload: UserPublicSchemaCreate,
    session: AsyncDBSession,
    hasher: PasswordHasherDep,
    sender: EmailSenderDep,
) -> Any:
    """Register user route: the new member gets a link to verify the address."""
    return await UserService.register(payload, session, hasher, sender)


@router.post(
    "/login/",
    summary="Log in with email and password",
    status_code=status.HTTP_200_OK,
    response_model=TokenPublicSchemaResponse,
    dependencies=[Depends(limit_auth_requests), Depends(limit_login_attempts)],
)
async def login_user_route(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncDBSession,
    hasher: PasswordHasherDep,
    codec: AccessTokenCodecDep,
) -> Any:
    """Login user route (OAuth 2.0 password flow: the username is the email)."""
    user = await AuthService.authenticate(form.username, form.password, session, hasher)
    return await AuthService.issue_tokens(user, session, codec)


@router.post(
    "/refresh/",
    summary="Get a new token pair from a refresh token",
    status_code=status.HTTP_200_OK,
    response_model=TokenPublicSchemaResponse,
)
async def refresh_token_route(
    payload: RefreshTokenPublicSchemaPayload,
    session: AsyncDBSession,
    codec: AccessTokenCodecDep,
) -> Any:
    """Refresh token route."""
    return await AuthService.refresh(payload.refresh_token, session, codec)


@router.post(
    "/logout/",
    summary="Log out, revoking the session of a refresh token",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_user_route(
    payload: RefreshTokenPublicSchemaPayload, session: AsyncDBSession
) -> None:
    """Logout user route."""
    await AuthService.logout(payload.refresh_token, session)


@router.post(
    "/email/verification/",
    summary="Send a new link to verify the current user's email address",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_auth_requests), Depends(limit_verification_emails)],
)
async def request_email_verification_route(
    user: AuthenticatedUser, session: AsyncDBSession, sender: EmailSenderDep
) -> None:
    """Request email verification route (nothing is sent if already verified)."""
    await AuthService.request_email_verification(user, session, sender)


@router.post(
    "/email/verify/",
    summary="Verify an email address with the token of the emailed link",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(limit_auth_requests)],
)
async def verify_email_route(
    payload: OneTimeTokenPublicSchemaPayload, session: AsyncDBSession
) -> None:
    """Verify email route."""
    await AuthService.verify_email(payload.token, session)


@router.post(
    "/password/forgot/",
    summary="Email a link to choose a new password",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_auth_requests), Depends(limit_password_reset_emails)],
)
async def forgot_password_route(
    payload: EmailPublicSchemaPayload, session: AsyncDBSession, sender: EmailSenderDep
) -> None:
    """Forgot password route: the same answer whether the email exists or not."""
    await AuthService.request_password_reset(payload.email, session, sender)


@router.post(
    "/password/reset/",
    summary="Choose a new password with the token of the emailed link",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(limit_auth_requests)],
)
async def reset_password_route(
    payload: PasswordResetPublicSchemaPayload,
    session: AsyncDBSession,
    hasher: PasswordHasherDep,
) -> None:
    """Reset password route: every session of the user ends."""
    await AuthService.reset_password(payload.token, payload.password, session, hasher)


@router.post(
    "/google/",
    summary="Sign in with a Google ID token",
    status_code=status.HTTP_200_OK,
    response_model=TokenPublicSchemaResponse,
    dependencies=[Depends(limit_auth_requests)],
)
async def login_google_user_route(
    payload: IdTokenPublicSchemaPayload,
    session: AsyncDBSession,
    provider: GoogleIdentityProviderDep,
    codec: AccessTokenCodecDep,
) -> Any:
    """Login Google user route (the frontend sends the ID token Google issued)."""
    user = await AuthService.authenticate_external(payload.id_token, provider, session)
    return await AuthService.issue_tokens(user, session, codec)


@router.post(
    "/google/link/",
    summary="Link a Google account to the current user",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(limit_auth_requests), Depends(limit_link_attempts)],
)
async def link_google_account_route(
    payload: IdTokenLinkPublicSchemaPayload,
    user: AuthenticatedUser,
    session: AsyncDBSession,
    provider: GoogleIdentityProviderDep,
    hasher: PasswordHasherDep,
) -> None:
    """Link Google account route (the password confirms it is the account owner)."""
    await AuthService.link_external(
        payload.id_token, payload.password, user, provider, session, hasher
    )


@router.get("/google/test-page/", include_in_schema=False)
async def google_test_page_route() -> HTMLResponse:
    """Google test page route: try Google sign-in locally, without a frontend."""
    # Why: a development aid, served only where the API docs are served.
    if not (settings.docs_enabled and settings.GOOGLE_CLIENT_ID):
        raise NotFoundHTTPException(message="Not Found")
    api_v1 = f"{settings.API_ROOT}/v1"
    page = (
        GOOGLE_TEST_PAGE.read_text()
        .replace("{{ GOOGLE_CLIENT_ID }}", html.escape(settings.GOOGLE_CLIENT_ID))
        .replace("{{ LOGIN_URL }}", html.escape(f"{api_v1}/auth/google/"))
        .replace("{{ ME_URL }}", html.escape(f"{api_v1}/users/user/me/"))
    )
    return HTMLResponse(page)
