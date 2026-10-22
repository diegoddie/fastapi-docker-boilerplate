"""The users package constants."""

from app.ai.constants import CAN_SUGGEST_TODO_SUBTASKS  # copier:ai
from app.todos.constants import (
    CAN_CREATE_TODO,
    CAN_DELETE_TODO,
    CAN_EDIT_TODO,
    CAN_MANAGE_ALL_TODOS,
    CAN_VIEW_TODO,
)
from app.users.enums import Group

EMAIL_MAX_LENGTH = 320
NAME_MAX_LENGTH = 150

CAN_VIEW_USER = "can_view_user"
CAN_EDIT_USER = "can_edit_user"
CAN_DISABLE_USER = "can_disable_user"

USER_PERMISSIONS = frozenset({CAN_VIEW_USER, CAN_EDIT_USER, CAN_DISABLE_USER})
TODO_PERMISSIONS = frozenset(
    {
        CAN_CREATE_TODO,
        CAN_VIEW_TODO,
        CAN_EDIT_TODO,
        CAN_DELETE_TODO,
        CAN_SUGGEST_TODO_SUBTASKS,  # copier:ai
    }
)

# Why: permissions are granted through groups and computed on every request, so
# changing a group here takes effect immediately, without logging users out.
GROUPS: dict[Group, frozenset[str]] = {
    Group.ADMIN: USER_PERMISSIONS | TODO_PERMISSIONS | {CAN_MANAGE_ALL_TODOS},
    Group.MEMBER: TODO_PERMISSIONS,
    Group.VIEWER: frozenset({CAN_VIEW_TODO}),
}

DEFAULT_GROUPS: tuple[Group, ...] = (Group.MEMBER,)
