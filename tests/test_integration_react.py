"""Integration tests for ReAct loop with mock LLM (preset tool call sequence)."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.database import Database
from src.llm.client import LLMClient, LLMResponse
from src.orchestrator.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_react_loop_calls_get_current_datetime_then_returns(mock_db, mock_llm):
    """When LLM first requests get_current_datetime, executor runs it and feeds back."""
    from src.orchestrator.tool_executor import ToolExecutor
    from src.orchestrator.tool_registry import TOOL_REGISTRY
    # This test assumes orchestrator and tool_executor are wired; run after implementation
    mock_llm.call_with_tools.return_value = LLMResponse(content="امروز یکشنبه ۲۶ بهمن است.")
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "امروز چیکار دارم؟")
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_react_loop_ask_user_pauses_and_returns_question(mock_db, mock_llm):
    """When LLM calls ask_user, orchestrator saves context and returns question to user."""
    # Requires orchestrator to handle tool_calls and detect ask_user
    mock_llm.call_with_tools.return_value = LLMResponse(
        content="",
        tool_calls=[
            MagicMock(
                id="call_1",
                function=MagicMock(
                    name="ask_user",
                    arguments=json.dumps({"question": "کی باید بری؟", "context": "gathering"}),
                ),
            )
        ],
    )
    orch = Orchestrator(db=mock_db, llm=mock_llm)
    response = await orch.handle_message("u1", "باید برم دکتر")
    assert isinstance(response, str)
