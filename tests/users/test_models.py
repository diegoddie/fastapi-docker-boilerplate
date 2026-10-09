"""The users package models tests."""

import pytest

from app.users.constants import CAN_DISABLE_USER, CAN_EDIT_USER, CAN_VIEW_USER
from app.users.enums import Group
from app.users.models import User


@pytest.mark.parametrize(
    ("groups", "permissions"),
    [
        ([Group.ADMIN], {CAN_VIEW_USER, CAN_EDIT_USER, CAN_DISABLE_USER}),
        ([Group.MEMBER], set()),
        ([Group.VIEWER], set()),
        ([], set()),
    ],
    ids=["admin", "member", "viewer", "no_groups"],
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
