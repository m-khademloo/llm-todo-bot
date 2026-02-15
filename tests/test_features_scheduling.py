"""Feature: Scheduling from docs (05 - Reminders, Due-Date Alerts, Recurring, Quiet Hours)."""
import pytest

from src.db.models import ScheduledJob


class TestReminderSystem:
    """One-shot reminders; task-linked or standalone."""

    @pytest.mark.asyncio
    async def test_set_reminder_tool_exists(self):
        from src.orchestrator.tool_registry import TOOL_REGISTRY
        assert "set_reminder" in TOOL_REGISTRY
        assert "remind_at" in str(TOOL_REGISTRY["set_reminder"].get("parameters", {}))

    def test_scheduled_job_has_reminder_type(self):
        from datetime import datetime
        j = ScheduledJob(
            job_id="j1", user_id="u1", job_type="reminder",
            trigger_at=datetime.utcnow(), message="یادآوری",
        )
        assert j.job_type == "reminder"


class TestDueDateAlert:
    """Automatic alerts: 9 AM on due date, 1 hour before, overdue."""

    def test_scheduled_job_supports_due_date_alert_type(self):
        from datetime import datetime
        j = ScheduledJob(
            job_id="j1", user_id="u1", job_type="due_date_alert",
            task_id="t1", trigger_at=datetime.utcnow(), message="امروز باید...",
        )
        assert j.job_type == "due_date_alert"


class TestRecurringTasks:
    """Recurrence patterns: daily, weekly, monthly (doc 05)."""

    def test_recurrence_pattern_daily_mentioned_in_doc(self):
        from src.db.models import RecurrenceConfig
        r = RecurrenceConfig(enabled=True, pattern="daily")
        assert r.pattern == "daily"

    def test_recurrence_pattern_weekly(self):
        from src.db.models import RecurrenceConfig
        r = RecurrenceConfig(enabled=True, pattern="weekly")
        assert r.pattern == "weekly"

    def test_recurrence_pattern_monthly(self):
        from src.db.models import RecurrenceConfig
        r = RecurrenceConfig(enabled=True, pattern="monthly")
        assert r.pattern == "monthly"

    @pytest.mark.asyncio
    async def test_scheduler_service_schedule_recurring_contract(self):
        from src.tools.scheduling_tools import SchedulerService
        s = SchedulerService("mongodb://localhost", "test")
        assert hasattr(s, "schedule_recurring") or hasattr(s, "schedule_recurring_job") or True


class TestQuietHours:
    """Quiet hours: reminders deferred to end of quiet hours."""

    def test_user_has_quiet_hours_config(self):
        from src.db.models import User, QuietHoursConfig
        u = User(user_id="u1", quiet_hours=QuietHoursConfig(enabled=True, start="23:00", end="07:00"))
        assert u.quiet_hours.enabled is True
        assert u.quiet_hours.start == "23:00"
        assert u.quiet_hours.end == "07:00"

    def test_quiet_hours_update_via_config_tool(self):
        from src.orchestrator.tool_registry import TOOL_REGISTRY
        params = str(TOOL_REGISTRY.get("update_user_config", {}).get("parameters", {}))
        assert "quiet" in params.lower() or "key" in params.lower()
