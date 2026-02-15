"""Feature: Telegram commands from docs (06 - The Only Exceptions)."""
import pytest

from src.utils.i18n import t


class TestStartCommand:
    """ /start — Universal reset, required by Telegram."""

    def test_start_returns_welcome_template(self):
        w = t("welcome", "fa")
        assert "سلام" in w or "دستیار" in w

    def test_start_welcome_available_in_en(self):
        w = t("welcome", "en")
        assert "Hi" in w or "assistant" in w.lower()


class TestHelpCommand:
    """ /help — Show brief help text."""

    def test_help_template_exists_fa(self):
        h = t("help", "fa")
        assert len(h) > 0
        assert "تسک" in h or "اضافه" in h or "لیست" in h

    def test_help_template_exists_en(self):
        h = t("help", "en")
        assert len(h) > 0
        assert "task" in h.lower() or "add" in h.lower() or "list" in h.lower()


class TestTasksCommand:
    """ /tasks — Quick shortcut for 'لیست تسک‌ها'."""

    def test_get_user_tasks_can_fulfill_tasks_shortcut(self):
        """ /tasks should be handled by same path as query_tasks (get_user_tasks)."""
        from src.orchestrator.tool_registry import TOOL_REGISTRY
        assert "get_user_tasks" in TOOL_REGISTRY


class TestCancelCommand:
    """ /cancel — Cancel current flow (same as /start but doesn't show welcome)."""

    def test_cancel_clears_context_like_start(self):
        """Contract: /cancel must clear saved conversation context (implementation may reuse /start logic)."""
        from src.db.database import Database
        assert hasattr(Database, "clear_conversation_context")
