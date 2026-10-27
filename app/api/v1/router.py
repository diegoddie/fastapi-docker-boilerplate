"""The v1 api package router."""

from fastapi import APIRouter

from app.ai.router import router as ai_router  # copier:ai
from app.auth.router import router as auth_router
from app.payments.router import router as payments_router  # copier:payments
from app.todos.router import router as todos_router
from app.users.router import router as users_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(todos_router, prefix="/todos", tags=["todos"])
router.include_router(ai_router, prefix="/todos", tags=["ai"])  # copier:ai
# copier:payments:start
router.include_router(payments_router, prefix="/payments", tags=["payments"])
# copier:payments:end
