"""The users package router."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.auth.dependencies import AuthenticatedUser, require_any_permissions
from app.commons.pagination import paginate
from app.core.database import AsyncDBSession
from app.users.constants import CAN_DISABLE_USER, CAN_EDIT_USER, CAN_VIEW_USER
from app.users.schemas import (
    UserMePublicSchemaUpdate,
    UserPublicSchemaResponse,
    UserPublicSchemaUpdate,
)
from app.users.services import UserService

router = APIRouter()


@router.get(
    "/user/me/",
    summary="Get the current user",
    status_code=status.HTTP_200_OK,
    response_model=UserPublicSchemaResponse,
)
async def me_user_route(user: AuthenticatedUser) -> Any:
    """Me user route."""
    return user


@router.patch(
    "/user/me/",
    summary="Update the current user",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_me_user_route(
    payload: UserMePublicSchemaUpdate, session: AsyncDBSession, user: AuthenticatedUser
) -> None:
    """Update me user route."""
    await UserService.update_me(user, payload, session)


@router.get(
    "/user/",
    summary="Get a list of all users",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserPublicSchemaResponse],
    dependencies=[Depends(require_any_permissions([CAN_VIEW_USER]))],
)
async def list_users_route(session: AsyncDBSession) -> Any:
    """List users route."""
    return await paginate(session, UserService.list_query())


@router.get(
    "/user/{user_id:uuid}/",
    summary="Get a user detail",
    status_code=status.HTTP_200_OK,
    response_model=UserPublicSchemaResponse,
    dependencies=[Depends(require_any_permissions([CAN_VIEW_USER]))],
)
async def detail_user_route(user_id: UUID, session: AsyncDBSession) -> Any:
    """Detail user route."""
    return await UserService.get_by_id(user_id, session)


@router.patch(
    "/user/{user_id:uuid}/",
    summary="Update a user",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_any_permissions([CAN_EDIT_USER]))],
)
async def update_user_route(
    user_id: UUID,
    payload: UserPublicSchemaUpdate,
    session: AsyncDBSession,
    user: AuthenticatedUser,
) -> None:
    """Update user route."""
    await UserService.update(user_id, payload, session, user)


@router.delete(
    "/user/{user_id:uuid}/",
    summary="Disable a user",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_any_permissions([CAN_DISABLE_USER]))],
)
async def delete_user_route(
    user_id: UUID, session: AsyncDBSession, user: AuthenticatedUser
) -> None:
    """Delete user route."""
    await UserService.disable(user_id, session, user)
