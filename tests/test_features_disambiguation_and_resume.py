"""Feature: Disambiguation (Pattern 4) and ReAct resume after ask_user (doc 02, 06)."""
import pytest


class TestDisambiguation:
    """Multiple tasks match; bot asks which one (via ask_user); LLM resolves 'اولی' etc from history."""

    @pytest.mark.asyncio
    async def test_get_user_tasks_can_return_multiple_for_same_user(self, mock_db, sample_tasks):
        """Disambiguation flow: get_user_tasks returns list; then ask_user can ask which one."""
        for t in sample_tasks:
            await mock_db.create_task(t)
        from src.tools import task_tools
        r = await task_tools.get_user_tasks(sample_tasks[0].user_id, mock_db)
        assert r["count"] >= 2
        assert len(r["tasks"]) >= 2

    @pytest.mark.asyncio
    async def test_ask_user_can_ask_which_task(self):
        """Bot can ask 'کدومو میگی؟' with numbered list in question."""
        from src.tools.conversation_tools import ask_user
        r = await ask_user(
            "u1",
            question="چند تا جلسه داری، کدومو میگی؟\n۱. جلسه الف\n۲. جلسه ب",
            context="disambiguate",
        )
        assert "۱" in r.get("question", "") or "جلسه" in r.get("question", "")
        assert r.get("waiting_for_response") is True


class TestReActResume:
    """Saved context resumed when user replies after ask_user."""

    @pytest.mark.asyncio
    async def test_save_context_stores_messages(self, mock_db):
        from src.orchestrator.state_manager import StateManager
        sm = StateManager(mock_db)
        messages = [
            {"role": "user", "content": "باید برم دکتر"},
            {"role": "assistant", "content": None, "tool_calls": [{"function": {"name": "ask_user", "arguments": "{}"}}]},
        ]
        await sm.save_context("u1", messages)
        ctx = await sm.get_saved_context("u1")
        assert ctx is not None
        assert len(ctx.get("messages", [])) == 2

    @pytest.mark.asyncio
    async def test_clear_context_on_start(self, mock_db):
        from src.orchestrator.state_manager import StateManager
        sm = StateManager(mock_db)
        await sm.save_context("u1", [{"role": "user", "content": "x"}])
        await sm.clear_context("u1")
        assert await sm.get_saved_context("u1") is None
