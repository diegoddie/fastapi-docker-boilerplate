"""The auth package router."""

import html
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import AuthenticatedUser
from app.auth.identity import GoogleIdentityProviderDep
from app.auth.schemas import (
    IdTokenLinkPublicSchemaPayload,
    IdTokenPublicSchemaPayload,
    RefreshTokenPublicSchemaPayload,
    TokenPublicSchemaResponse,
)
from app.auth.security import AccessTokenCodecDep, PasswordHasherDep
from app.auth.services import AuthService
from app.core.config import settings
from app.core.database import AsyncDBSession
from app.core.exceptions import NotFoundHTTPException
from app.users.schemas import UserPublicSchemaCreate, UserPublicSchemaResponse
from app.users.services import UserService

router = APIRouter()

GOOGLE_TEST_PAGE = Path(__file__).parent / "templates" / "google_sign_in.html"


@router.post(
    "/register/",
    summary="Register a new user",
    status_code=status.HTTP_201_CREATED,
    response_model=UserPublicSchemaResponse,
)
async def register_user_route(
    payload: UserPublicSchemaCreate, session: AsyncDBSession, hasher: PasswordHasherDep
) -> Any:
    """Register user route."""
    return await UserService.create(payload, session, hasher)


@router.post(
    "/login/",
    summary="Log in with email and password",
    status_code=status.HTTP_200_OK,
    response_model=TokenPublicSchemaResponse,
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
    "/google/",
    summary="Sign in with a Google ID token",
    status_code=status.HTTP_200_OK,
    response_model=TokenPublicSchemaResponse,
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
