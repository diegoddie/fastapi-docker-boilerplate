"""The ai package services tests."""

import anthropic
import pytest
from langchain_core.messages import HumanMessage

from app.ai.schemas import SubtaskPlan
from app.ai.services import generate
from app.users.models import User
from tests.pytest_plugins.ai import FakeChatModel


@pytest.mark.asyncio(loop_scope="function")
async def test_generate_request_error(
    fake_chat_model: FakeChatModel, bob_member_user: User
) -> None:
    """Test a rejected request is not taken for an outage: it is a bug to see."""
    fake_chat_model.fail(400)
    with pytest.raises(anthropic.APIStatusError):
        await generate(
            fake_chat_model,
            [HumanMessage("Plan this")],
            SubtaskPlan,
            name="test",
            user=bob_member_user,
            callbacks=[],
        )
