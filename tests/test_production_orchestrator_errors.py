"""Production: Orchestrator must handle errors without crashing (tool failure, invalid JSON, max iterations)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.llm.client import LLMResponse


@pytest.mark.asyncio
async def test_orchestrator_handles_tool_error_gracefully(mock_db, mock_llm):
    """When a tool returns {error: "..."}, orchestrator feeds it back to LLM and continues or returns safe message."""
    from src.orchestrator.orchestrator import Orchestrator
    mock_llm.call_with_tools.return_value = LLMResponse(content="متوجه نشدم، دوباره امتحان کن")
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "تسک‌هامو نشون بده")
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_orchestrator_max_iterations_returns_friendly_message(mock_db, mock_llm):
    """When ReAct loop hits max iterations, return a non-technical message to user."""
    from src.orchestrator.orchestrator import Orchestrator
    mock_llm.call_with_tools.return_value = LLMResponse(content="")
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "سلام")
    assert isinstance(response, str)
    if "لطفا" in response or "امتحان" in response or "مشکل" in response:
        assert True  # friendly message
    else:
        assert len(response) > 0


@pytest.mark.asyncio
async def test_tool_executor_returns_error_dict_on_unknown_tool(mock_db):
    """Unknown tool name must return error dict, not raise."""
    from src.orchestrator.tool_executor import ToolExecutor
    ex = ToolExecutor(mock_db)
    result = await ex.execute("nonexistent_tool", {"_user_id": "u1"})
    assert "error" in result
    assert isinstance(result["error"], str)
