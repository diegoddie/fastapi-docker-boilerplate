"""The auth package router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.schemas import RefreshTokenPublicSchemaPayload, TokenPublicSchemaResponse
from app.auth.security import AccessTokenCodecDep, PasswordHasherDep
from app.auth.services import AuthService
from app.core.database import AsyncDBSession
from app.users.schemas import UserPublicSchemaCreate, UserPublicSchemaResponse
from app.users.services import UserService

router = APIRouter()


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
