"""The todos test factories."""

from datetime import date

from app.todos.enums import TodoPriority, TodoStatus
from app.todos.models import Todo
from tests.factories.base import BaseFactory


class TodoFactory(BaseFactory[Todo]):
    """A todo factory (pass the owner_id: there is no default owner)."""

    __model__ = Todo

    datetime_disabled = None

    @classmethod
    def title(cls) -> str:
        """Return a fake title."""
        return str(cls.__faker__.sentence(nb_words=4))

    @classmethod
    def description(cls) -> str:
        """Return a fake description."""
        return str(cls.__faker__.sentence())

    @classmethod
    def status(cls) -> TodoStatus:
        """Return a random status."""
        return cls.__faker__.random_element(list(TodoStatus))

    @classmethod
    def priority(cls) -> TodoPriority:
        """Return a random priority."""
        return cls.__faker__.random_element(list(TodoPriority))

    @classmethod
    def due_date(cls) -> date:
        """Return a due date in 2026."""
        return cls.__faker__.date_between(date(2026, 1, 1), date(2026, 12, 31))
