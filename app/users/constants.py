"""The users package constants."""

from app.users.enums import Group

CAN_VIEW_USER = "can_view_user"
CAN_EDIT_USER = "can_edit_user"
CAN_DISABLE_USER = "can_disable_user"

# Why: permissions are granted through groups and computed on every request, so
# changing a group here takes effect immediately, without logging users out.
GROUPS: dict[Group, frozenset[str]] = {
    Group.ADMIN: frozenset({CAN_VIEW_USER, CAN_EDIT_USER, CAN_DISABLE_USER}),
    Group.MEMBER: frozenset(),
    Group.VIEWER: frozenset(),
}

DEFAULT_GROUPS: tuple[Group, ...] = (Group.MEMBER,)
