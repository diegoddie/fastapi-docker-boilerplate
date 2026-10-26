"""The ai package dependencies tests."""

import pytest
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

from app.ai.dependencies import build_chat_model, get_chat_model
from app.core.config import settings


def test_build_chat_model_disabled() -> None:
    """Test there is no chat model without an API key."""
    assert build_chat_model() is None


def test_build_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the chat model fits Claude Opus 5.5, and is created once."""
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", SecretStr("sk-ant-test"))
    chat_model = build_chat_model()
    assert isinstance(chat_model, ChatAnthropic)
    assert chat_model is build_chat_model()
    assert get_chat_model() is chat_model
    assert (chat_model.model, chat_model.max_tokens) == ("claude-opus-5-5", 16000)
    assert chat_model.thinking == {"type": "adaptive"}
    assert chat_model.reasoning_effort == "medium"
    assert chat_model.betas == ["server-side-fallback-2026-07-01"]
    assert chat_model.model_kwargs == {"fallbacks": "default"}
    # The current models reject the sampling parameters.
    assert (chat_model.temperature, chat_model.top_p, chat_model.top_k) == (
        None,
        None,
        None,
    )
    assert (chat_model.default_request_timeout, chat_model.max_retries) == (60, 1)
