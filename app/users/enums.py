"""The users package enums."""

from enum import StrEnum


class Group(StrEnum):
    """A user group: each group grants a set of permissions (see GROUPS)."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    # Why: given and taken by the payments, from the user's subscriptions.
    PRO = "pro"  # copier:payments
