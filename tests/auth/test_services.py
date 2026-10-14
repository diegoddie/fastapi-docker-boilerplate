"""The auth package services tests."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import RefreshToken
from app.auth.services import AuthService
from app.users.models import User
from tests.factories.auth import RefreshTokenFactory


@pytest.mark.asyncio(loop_scope="function")
async def test_purge_expired_tokens(
    async_db_session: AsyncSession,
    refresh_token_factory: type[RefreshTokenFactory],
    bob_member_user: User,
) -> None:
    """Test only expired tokens are deleted: revoked ones still detect theft."""
    now = datetime.now(UTC)
    active = await refresh_token_factory.create_async(user_id=bob_member_user.id)
    revoked = await refresh_token_factory.create_async(
        user_id=bob_member_user.id, datetime_revoked=now
    )
    for revoked_at in (None, now - timedelta(days=2)):
        await refresh_token_factory.create_async(
            user_id=bob_member_user.id,
            datetime_expires=now - timedelta(seconds=1),
            datetime_revoked=revoked_at,
        )
    assert await AuthService.purge_expired_tokens(async_db_session) == 2
    remaining = (await async_db_session.exec(select(RefreshToken.id))).all()
    assert set(remaining) == {active.id, revoked.id}
