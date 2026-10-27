"""The users package models tests."""

import pytest

from app.ai.constants import CAN_SUGGEST_TODO_SUBTASKS  # copier:ai
from app.payments.constants import CAN_USE_PRO_FEATURES  # copier:payments
from app.todos.constants import (
    CAN_CREATE_TODO,
    CAN_DELETE_TODO,
    CAN_EDIT_TODO,
    CAN_MANAGE_ALL_TODOS,
    CAN_VIEW_TODO,
)
from app.users.constants import CAN_DISABLE_USER, CAN_EDIT_USER, CAN_VIEW_USER
from app.users.enums import Group
from app.users.models import User


@pytest.mark.parametrize(
    ("groups", "permissions"),
    [
        (
            [Group.ADMIN],
            {
                CAN_VIEW_USER,
                CAN_EDIT_USER,
                CAN_DISABLE_USER,
                CAN_CREATE_TODO,
                CAN_VIEW_TODO,
                CAN_EDIT_TODO,
                CAN_DELETE_TODO,
                CAN_MANAGE_ALL_TODOS,
                CAN_SUGGEST_TODO_SUBTASKS,  # copier:ai
            },
        ),
        (
            [Group.MEMBER],
            {
                CAN_CREATE_TODO,
                CAN_VIEW_TODO,
                CAN_EDIT_TODO,
                CAN_DELETE_TODO,
                CAN_SUGGEST_TODO_SUBTASKS,  # copier:ai
            },
        ),
        ([Group.VIEWER], {CAN_VIEW_TODO}),
        (
            [Group.VIEWER, Group.MEMBER],
            {
                CAN_CREATE_TODO,
                CAN_VIEW_TODO,
                CAN_EDIT_TODO,
                CAN_DELETE_TODO,
                CAN_SUGGEST_TODO_SUBTASKS,  # copier:ai
            },
        ),
        ([], set()),
        ([Group.PRO], {CAN_USE_PRO_FEATURES}),  # copier:payments
    ],
    ids=[
        "admin",
        "member",
        "viewer",
        "several_groups",
        "no_groups",
        "pro",  # copier:payments
    ],
)
def test_user_permissions(groups: list[str], permissions: set[str]) -> None:
    """Test a user has the union of the permissions of their groups."""
    user = User(email="user@example.com", first_name="A", last_name="B", groups=groups)
    assert user.permissions == permissions


def test_user_is_active() -> None:
    """Test a user is active until disabled."""
    user = User(email="user@example.com", first_name="A", last_name="B")
    assert user.is_active is True
    assert user.groups == [Group.MEMBER]
