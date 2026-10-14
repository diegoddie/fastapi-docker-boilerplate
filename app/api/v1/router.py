"""The v1 api package router."""

from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.todos.router import router as todos_router
from app.users.router import router as users_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(todos_router, prefix="/todos", tags=["todos"])
