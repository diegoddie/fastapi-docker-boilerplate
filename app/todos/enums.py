"""The todos package enums."""

from enum import StrEnum


class TodoStatus(StrEnum):
    """The progress of a todo."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TodoPriority(StrEnum):
    """The priority of a todo, in increasing order (the database sorts it so)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
