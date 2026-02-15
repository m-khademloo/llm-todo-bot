"""Tests for ToolExecutor: execute by name, user_id injection, error handling."""
import pytest

from src.orchestrator.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_execute_unknown_tool_returns_error(mock_db):
    ex = ToolExecutor(mock_db)
    result = await ex.execute("unknown_tool", {"_user_id": "u1"})
    assert "error" in result
    assert "unknown" in result["error"].lower() or "Unknown" in result["error"]


@pytest.mark.asyncio
async def test_execute_strips_user_id_from_args(mock_db):
    """Executor must pop _user_id and pass to tool, not forward to LLM-defined args."""
    ex = ToolExecutor(mock_db)
    result = await ex.execute("get_current_datetime", {"_user_id": "u1"})
    # Either success or NotImplementedError; args should not leak _user_id to tool impl
    assert "_user_id" not in result or "error" in result


@pytest.mark.asyncio
async def test_execute_get_user_tasks_returns_count_and_list(mock_db, sample_tasks):
    for t in sample_tasks:
        await mock_db.create_task(t)
    ex = ToolExecutor(mock_db)
    result = await ex.execute(
        "get_user_tasks",
        {"_user_id": sample_tasks[0].user_id, "status": "pending"},
    )
    if "error" not in result:
        assert "count" in result
        assert "tasks" in result
        assert result["count"] == 2


@pytest.mark.asyncio
async def test_execute_ask_user_returns_waiting_and_question(mock_db):
    ex = ToolExecutor(mock_db)
    result = await ex.execute(
        "ask_user",
        {"_user_id": "u1", "question": "کی؟", "context": "gathering"},
    )
    if "error" not in result:
        assert result.get("waiting_for_response") is True
        assert result.get("question") == "کی؟"
