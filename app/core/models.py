"""
The core models.

Every table model must be imported here: Alembic autogenerate and the test
database setup import this module to populate ``SQLModel.metadata``.
"""

from app.auth.models import ExternalIdentity, OneTimeToken, RefreshToken
from app.payments.models import Subscription, WebhookEvent  # copier:payments
from app.ratelimit.models import RateLimitCounter
from app.todos.models import Todo
from app.users.models import User

__all__ = [
    "ExternalIdentity",
    "OneTimeToken",
    "RateLimitCounter",
    "RefreshToken",
    "Subscription",  # copier:payments
    "Todo",
    "User",
    "WebhookEvent",  # copier:payments
]
