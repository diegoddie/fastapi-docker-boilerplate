"""The payments and users tests: the pro group follows the subscriptions."""

import pytest
from fastapi import status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.users.enums import Group
from app.users.models import User
from tests.utils import AsyncClient


@pytest.mark.asyncio(loop_scope="function")
async def test_update_user_route_204_keeps_pro(
    async_client: AsyncClient,
    async_db_session: AsyncSession,
    alice_admin_user: User,
    bob_member_user: User,
    carol_viewer_user: User,
) -> None:
    """Test an administrator neither takes the pro group away nor grants it."""
    bob_member_user.groups = [Group.MEMBER, Group.PRO]
    async_db_session.add(bob_member_user)
    await async_db_session.commit()
    async_client.login(alice_admin_user)
    for user, groups in [
        (bob_member_user, ["viewer"]),
        (carol_viewer_user, ["viewer", "pro"]),
    ]:
        response = await async_client.patch(
            f"/api/v1/users/user/{user.id}/", json={"groups": groups}
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
    async_db_session.expunge_all()
    bob = await async_db_session.get(User, bob_member_user.id)
    carol = await async_db_session.get(User, carol_viewer_user.id)
    assert bob is not None
    assert carol is not None
    assert (bob.groups, carol.groups) == ([Group.VIEWER, Group.PRO], [Group.VIEWER])
