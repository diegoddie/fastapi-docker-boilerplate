"""
The core models.

Every table model must be imported here: Alembic autogenerate and the test
database setup import this module to populate ``SQLModel.metadata``.
"""

from app.auth.models import ExternalIdentity, RefreshToken
from app.ratelimit.models import RateLimitCounter
from app.todos.models import Todo
from app.users.models import User

__all__ = [
    "ExternalIdentity",
    "RateLimitCounter",
    "RefreshToken",
    "Todo",
    "User",
]
