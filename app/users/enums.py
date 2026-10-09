"""The users package enums."""

from enum import StrEnum


class Group(StrEnum):
    """A user group: each group grants a set of permissions (see GROUPS)."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
