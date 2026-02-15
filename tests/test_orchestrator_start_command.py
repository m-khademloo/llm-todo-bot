"""Tests for /start command: must work without LLM, clear context, return welcome."""
import pytest

from src.utils.i18n import t


def test_welcome_text_contains_fa_hello():
    """Static welcome for /start should be in Persian or contain greeting."""
    w = t("welcome", "fa")
    assert "سلام" in w or "دستیار" in w


def test_welcome_text_en():
    w = t("welcome", "en")
    assert "Hi" in w or "assistant" in w.lower()


@pytest.mark.asyncio
async def test_start_clears_any_saved_context(mock_db, mock_llm):
    """When user sends /start, saved ReAct context must be cleared."""
    from src.orchestrator.orchestrator import Orchestrator
    await mock_db.save_conversation_context("u1", [{"role": "user", "content": "x"}])
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "/start")
    ctx = await mock_db.get_conversation_context("u1")
    assert ctx is None
    assert len(response) > 0
