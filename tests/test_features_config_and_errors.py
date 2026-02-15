"""Feature: Config fields (06) and error/confusion handling (04, 06)."""
import pytest

from src.db.models import User, TaskCategory
from src.utils.i18n import t


class TestConfigFields:
    """All config fields from doc 06 - User Configuration System."""

    def test_user_has_language(self):
        u = User(user_id="u1")
        assert hasattr(u, "language")
        assert u.language == "fa"

    def test_user_has_timezone(self):
        u = User(user_id="u1")
        assert u.timezone == "Asia/Tehran"

    def test_user_has_priority_prompt(self):
        u = User(user_id="u1", priority_prompt="Health first")
        assert u.priority_prompt == "Health first"

    def test_user_has_default_category(self):
        u = User(user_id="u1")
        assert u.default_category == "personal"

    def test_user_has_notification_enabled(self):
        u = User(user_id="u1")
        assert u.notification_enabled is True

    def test_user_has_quiet_hours(self):
        u = User(user_id="u1")
        assert hasattr(u, "quiet_hours")
        assert u.quiet_hours.start == "23:00" and u.quiet_hours.end == "07:00"

    def test_update_user_config_accepts_key_value(self):
        from src.orchestrator.tool_registry import TOOL_REGISTRY
        p = TOOL_REGISTRY["update_user_config"].get("parameters", {})
        assert "key" in str(p) and "value" in str(p)


class TestErrorAndConfusionHandling:
    """Error handling & edge cases from doc 04 and 06."""

    def test_error_generic_template_for_mongo_or_technical(self):
        """MongoDB connection lost / technical: 'یه مشکل فنی پیش اومده'."""
        msg = t("error_generic", "fa")
        assert len(msg) > 0
        assert "مشکل" in msg or "فنی" in msg or "امتحان" in msg

    def test_error_rate_limit_template(self):
        """Too many messages: 'یکم آروم‌تر'."""
        msg = t("error_rate_limit", "fa")
        assert "آروم" in msg or "صبر" in msg

    def test_no_tasks_message_for_empty_list(self):
        """0 tasks: 'هیچ تسکی نداری'."""
        msg = t("no_tasks", "fa")
        assert "تسک" in msg or "نداری" in msg or "استراحت" in msg


class TestCategorySystem:
    """Predefined categories from doc 04 - Category System."""

    def test_all_six_predefined_categories_exist(self):
        assert TaskCategory.HEALTH.value == "health"
        assert TaskCategory.WORK.value == "work"
        assert TaskCategory.FAMILY.value == "family"
        assert TaskCategory.LEARNING.value == "learning"
        assert TaskCategory.PERSONAL.value == "personal"
        assert TaskCategory.OTHER.value == "other"

    def test_create_task_accepts_category_enum_values(self):
        from src.db.models import Task
        for cat in TaskCategory:
            t = Task(user_id="u1", title="x", category=cat)
            assert t.category == cat
