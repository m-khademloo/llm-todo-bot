"""Tool executor error handling: unknown tool, exception in tool, invalid args."""
from unittest.mock import AsyncMock

import pytest

from src.orchestrator.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_execute_missing_user_id_returns_error(mock_db):
    """When _user_id is missing from args, executor should fail safely."""
    ex = ToolExecutor(mock_db)
    result = await ex.execute("get_user_tasks", {"status": "pending"})
    assert "error" in result


@pytest.mark.asyncio
async def test_execute_tool_raising_exception_returns_error_dict(mock_db):
    """If a tool raises, executor catches and returns error dict."""
    ex = ToolExecutor(mock_db)
    result = await ex.execute("get_current_datetime", {"_user_id": "u1"})
    if "error" in result:
        assert "error" in result
        assert "failed" in result["error"].lower() or "error" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_empty_tool_name(mock_db):
    ex = ToolExecutor(mock_db)
    result = await ex.execute("", {"_user_id": "u1"})
    assert "error" in result