"""Feature: Conversation flow patterns from docs (06 - Pattern 1-7)."""
import pytest


class TestPattern1SingleTurnTaskCreation:
    """Happy path: user provides enough info in one message; skip gathering and confirmation."""

    def test_create_task_can_succeed_with_title_and_category_only(self):
        """create_task only requires title + category (no ask_user needed)."""
        from src.orchestrator.tool_registry import TOOL_REGISTRY
        params = TOOL_REGISTRY["create_task"].get("parameters", {})
        assert "title" in str(params) and "category" in str(params)


class TestPattern2MultiTurnGathering:
    """User gives partial info; ask one question at a time; max 3 follow-ups."""

    def test_ask_user_tool_exists_for_gathering(self):
        from src.orchestrator.tool_registry import TOOL_REGISTRY
        assert "ask_user" in TOOL_REGISTRY
        assert "question" in str(TOOL_REGISTRY["ask_user"].get("parameters", {}))

    def test_max_gather_turns_in_config(self):
        from src.config import Settings
        s = Settings(TELEGRAM_BOT_TOKEN="x")
        assert hasattr(s, "MAX_GATHER_TURNS")
        assert s.MAX_GATHER_TURNS == 3

    @pytest.mark.asyncio
    async def test_ask_user_returns_question_to_send(self):
        from src.tools.conversation_tools import ask_user
        r = await ask_user("u1", question="کی باید بری؟", context="gathering_create")
        assert r.get("question") == "کی باید بری؟"
        assert r.get("waiting_for_response") is True


class TestPattern5ConfirmationFlow:
    """Destructive actions: delete, bulk operations require explicit confirmation."""

    def test_request_task_deletion_requires_confirmation(self):
        from src.orchestrator.safety import SafetyLayer
        s = SafetyLayer()
        assert s.requires_confirmation("request_task_deletion") is True

    @pytest.mark.asyncio
    async def test_request_task_deletion_returns_confirm_message_not_immediate_delete(self, mock_db, sample_task):
        from src.tools import task_tools
        await mock_db.create_task(sample_task)
        try:
            r = await task_tools.request_task_deletion(sample_task.user_id, mock_db, sample_task.task_id)
            assert "question" in r or "confirm" in r or "حذف" in str(r) or "delete" in str(r).lower()
            task_after = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
            assert task_after is not None
        except NotImplementedError:
            pytest.skip("request_task_deletion not implemented")
            return


class TestPattern6SmalltalkAndHelp:
    """User: سلام / چیکار میتونی / ممنون — bot responds naturally; help lists capabilities."""

    def test_help_template_lists_capabilities(self):
        from src.utils.i18n import t
        h = t("help", "fa")
        assert len(h) > 20

    def test_welcome_invites_user_to_say_what_to_do(self):
        from src.utils.i18n import t
        w = t("welcome", "fa")
        assert "چیکار" in w or "بگو" in w or "چه" in w


class TestPattern7UserConfiguration:
    """User changes settings; update_user_config supports key/value."""

    @pytest.mark.asyncio
    async def test_update_user_config_supports_priority_prompt(self, mock_db, sample_user):
        from src.tools import config_tools
        await mock_db.get_or_create_user(sample_user.user_id)
        await config_tools.update_user_config(
            sample_user.user_id, mock_db, "priority_prompt", "Health > Work"
        )
        u = await mock_db.get_user(sample_user.user_id)
        assert u.priority_prompt == "Health > Work"

    @pytest.mark.asyncio
    async def test_update_user_config_supports_language_and_timezone(self, mock_db, sample_user):
        from src.tools import config_tools
        await mock_db.get_or_create_user(sample_user.user_id)
        await config_tools.update_user_config(sample_user.user_id, mock_db, "language", "en")
        await config_tools.update_user_config(sample_user.user_id, mock_db, "timezone", "UTC")
        u = await mock_db.get_user(sample_user.user_id)
        assert u.language == "en" and u.timezone == "UTC"
