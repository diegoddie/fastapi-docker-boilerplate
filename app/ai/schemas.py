"""The ai package schemas."""

from pydantic import BaseModel, Field

from app.ai.constants import MAX_SUBTASKS, MIN_SUBTASKS
from app.commons.schemas import BasePublicSchema
from app.todos.enums import TodoPriority
from app.todos.schemas import Description, Title


class Subtask(BaseModel):
    """A subtask: one step towards the todo, small enough to be a todo itself."""

    title: Title = Field(description="Short and actionable, e.g. 'Book the venue'.")
    description: Description = Field(
        description="What to do, and how to tell it is done, in one or two sentences."
    )
    priority: TodoPriority


class SubtaskPlan(BaseModel):
    """
    The subtasks that complete a todo, in the order to do them.

    Why: the schema the model answers in; its docstring and field descriptions
    are part of the prompt.
    """

    subtasks: list[Subtask] = Field(min_length=MIN_SUBTASKS, max_length=MAX_SUBTASKS)


class SubtaskSuggestionPublicSchema(BasePublicSchema):
    """A suggested subtask, ready to be sent to the create todo route."""

    title: str
    description: str
    priority: TodoPriority


class SubtaskSuggestionsPublicSchemaResponse(BasePublicSchema):
    """The subtask suggestions public schema response."""

    subtasks: list[SubtaskSuggestionPublicSchema]
