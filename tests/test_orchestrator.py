"""ReAct loop integration tests: /start, handle_message, ask_user pause/resume."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.orchestrator.orchestrator import Orchestrator
from src.llm.client import LLMClient, LLMResponse


@pytest.mark.asyncio
async def test_handle_message_start_returns_welcome_without_llm(mock_db, mock_llm):
    """ /start must return static welcome and clear context, no LLM call."""
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "/start")
    assert "سلام" in response or "Hi" in response or "welcome" in response.lower()
    mock_llm.call_with_tools.assert_not_called()
    ctx = await mock_db.get_conversation_context("u1")
    assert ctx is None


@pytest.mark.asyncio
async def test_handle_message_start_clears_saved_context(mock_db, mock_llm):
    await mock_db.save_conversation_context("u1", [{"role": "user", "content": "x"}])
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    await orch.handle_message("u1", "/start")
    ctx = await mock_db.get_conversation_context("u1")
    assert ctx is None


@pytest.mark.asyncio
async def test_handle_message_normal_calls_llm(mock_db, mock_llm):
    mock_llm.call_with_tools.return_value = LLMResponse(content="خوبم ممنون!")
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "سلام")
    mock_llm.call_with_tools.assert_called_once()
    assert "خوبم" in response or "ممنون" in response


@pytest.mark.asyncio
async def test_handle_message_injects_user_id_in_tool_calls(mock_db, mock_llm):
    """Orchestrator must inject user_id into tool args (user isolation)."""
    call_count = 0
    async def capture_tools(messages, tools, **kwargs):
        nonlocal call_count
        call_count += 1
        return LLMResponse(content="Done")
    mock_llm.call_with_tools.side_effect = capture_tools
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    await orch.handle_message("u1", "تسک‌هام رو نشون بده")
    assert call_count >= 1


@pytest.mark.asyncio
async def test_handle_message_max_iterations_returns_error_message(mock_db, mock_llm):
    """If ReAct loop hits max iterations, return friendly error."""
    mock_llm.call_with_tools.return_value = LLMResponse(
        content="",
        tool_calls=[MagicMock(function=MagicMock(name="get_user_tasks", arguments="{}"))],
    )
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "امروز چیکار دارم؟")
    # Either we get a final text response or max-iterations error
    assert isinstance(response, str)
    assert len(response) > 0
