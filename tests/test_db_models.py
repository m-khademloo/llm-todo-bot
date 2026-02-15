"""Tests for Pydantic models: Task, User, ReminderConfig, etc."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.db.models import (
    Task,
    TaskCategory,
    TaskStatus,
    User,
    ReminderConfig,
    RecurrenceConfig,
    QuietHoursConfig,
    SavedReActContext,
    TaskFilter,
    ScheduledJob,
)


# --- Task ---


class TestTask:
    def test_task_minimal(self):
        t = Task(user_id="u1", title="Test task")
        assert t.user_id == "u1"
        assert t.title == "Test task"
        assert t.task_id
        assert len(t.task_id) == 8
        assert t.status == TaskStatus.PENDING
        assert t.priority == 3
        assert t.category == TaskCategory.PERSONAL
        assert t.created_at is not None
        assert t.updated_at is not None
        assert t.completed_at is None

    def test_task_full(self):
        due = datetime(2026, 2, 16, 10, 0)
        t = Task(
            user_id="u1",
            title="جلسه",
            description="جلسه تیم",
            due_date=due,
            priority=1,
            category=TaskCategory.WORK,
            status=TaskStatus.PENDING,
            estimated_time_minutes=60,
            tags=["work"],
        )
        assert t.due_date == due
        assert t.priority == 1
        assert t.estimated_time_minutes == 60
        assert t.tags == ["work"]

    def test_task_priority_bounds(self):
        Task(user_id="u1", title="x", priority=1)
        Task(user_id="u1", title="x", priority=5)
        with pytest.raises(ValidationError):
            Task(user_id="u1", title="x", priority=0)
        with pytest.raises(ValidationError):
            Task(user_id="u1", title="x", priority=6)

    def test_task_category_enum(self):
        t = Task(user_id="u1", title="x", category=TaskCategory.HEALTH)
        assert t.category == TaskCategory.HEALTH
        t = Task(user_id="u1", title="x", category="health")
        assert t.category == TaskCategory.HEALTH

    def test_task_status_enum(self):
        t = Task(user_id="u1", title="x", status=TaskStatus.DONE)
        assert t.status == TaskStatus.DONE

    def test_task_reminder_default(self):
        t = Task(user_id="u1", title="x")
        assert t.reminder.enabled is False
        assert t.reminder.remind_at is None
        assert t.reminder.reminded is False

    def test_task_recurrence_default(self):
        t = Task(user_id="u1", title="x")
        assert t.recurrence.enabled is False
        assert t.recurrence.pattern is None


# --- User ---


class TestUser:
    def test_user_minimal(self):
        u = User(user_id="u1")
        assert u.user_id == "u1"
        assert u.language == "fa"
        assert u.timezone == "Asia/Tehran"
        assert u.default_category == "personal"
        assert u.notification_enabled is True
        assert u.message_count == 0
        assert u.task_count == 0

    def test_user_full(self):
        u = User(
            user_id="u1",
            telegram_username="test",
            first_name="Test",
            last_name="User",
            language="en",
            timezone="UTC",
            priority_prompt="Health > Work",
        )
        assert u.telegram_username == "test"
        assert u.priority_prompt == "Health > Work"

    def test_user_quiet_hours_default(self):
        u = User(user_id="u1")
        assert u.quiet_hours.enabled is False
        assert u.quiet_hours.start == "23:00"
        assert u.quiet_hours.end == "07:00"


# --- ReminderConfig ---


class TestReminderConfig:
    def test_reminder_config_default(self):
        r = ReminderConfig()
        assert r.enabled is False
        assert r.remind_at is None
        assert r.reminded is False


# --- RecurrenceConfig ---


class TestRecurrenceConfig:
    def test_recurrence_config_default(self):
        r = RecurrenceConfig()
        assert r.enabled is False
        assert r.pattern is None
        assert r.next_occurrence is None
        assert r.end_date is None


# --- SavedReActContext ---


class TestSavedReActContext:
    def test_saved_react_context(self):
        ctx = SavedReActContext(
            user_id="u1",
            messages=[{"role": "user", "content": "hello"}],
        )
        assert ctx.user_id == "u1"
        assert len(ctx.messages) == 1
        assert ctx.updated_at is not None


# --- TaskFilter ---


class TestTaskFilter:
    def test_task_filter_empty(self):
        f = TaskFilter()
        assert f.status is None
        assert f.category is None

    def test_task_filter_filled(self):
        due_from = datetime(2026, 2, 1)
        due_to = datetime(2026, 2, 28)
        f = TaskFilter(
            status="pending",
            category="work",
            due_date_from=due_from,
            due_date_to=due_to,
        )
        assert f.status == "pending"
        assert f.category == "work"
        assert f.due_date_from == due_from
        assert f.due_date_to == due_to


# --- ScheduledJob ---


class TestScheduledJob:
    def test_scheduled_job(self):
        trigger = datetime(2026, 2, 16, 9, 0)
        j = ScheduledJob(
            job_id="j1",
            user_id="u1",
            job_type="reminder",
            task_id="t1",
            trigger_at=trigger,
            message="یادآوری",
        )
        assert j.job_id == "j1"
        assert j.status == "pending"
        assert j.trigger_at == trigger
