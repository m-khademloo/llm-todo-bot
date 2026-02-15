"""State save/resume tests: conversation context for ReAct pause."""
import pytest

from src.orchestrator.state_manager import StateManager


@pytest.mark.asyncio
async def test_get_saved_context_empty(mock_db):
    sm = StateManager(mock_db)
    ctx = await sm.get_saved_context("u1")
    assert ctx is None


@pytest.mark.asyncio
async def test_save_and_get_context(mock_db):
    sm = StateManager(mock_db)
    messages = [
        {"role": "system", "content": "You are a task assistant."},
        {"role": "user", "content": "باید برم دکتر"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "1", "function": {"name": "ask_user", "arguments": "{}"}}]},
    ]
    await sm.save_context("u1", messages)
    ctx = await sm.get_saved_context("u1")
    assert ctx is not None
    assert "messages" in ctx
    assert len(ctx["messages"]) == 3


@pytest.mark.asyncio
async def test_clear_context(mock_db):
    sm = StateManager(mock_db)
    await sm.save_context("u1", [{"role": "user", "content": "x"}])
    ok = await sm.clear_context("u1")
    assert ok is True
    ctx = await sm.get_saved_context("u1")
    assert ctx is None


@pytest.mark.asyncio
async def test_context_is_per_user(mock_db):
    sm = StateManager(mock_db)
    await sm.save_context("u1", [{"role": "user", "content": "from u1"}])
    await sm.save_context("u2", [{"role": "user", "content": "from u2"}])
    ctx1 = await sm.get_saved_context("u1")
    ctx2 = await sm.get_saved_context("u2")
    assert ctx1["messages"][0]["content"] == "from u1"
    assert ctx2["messages"][0]["content"] == "from u2"
