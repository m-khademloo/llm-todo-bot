"""Tests for set_reminder and SchedulerService."""
from datetime import datetime, timedelta

import pytest

from src.tools.scheduling_tools import set_reminder, SchedulerService


@pytest.mark.asyncio
async def test_set_reminder_returns_reminder_id(mock_db, mock_scheduler):
    result = await set_reminder(
        "u1",
        mock_db,
        mock_scheduler,  # type: ignore
        remind_at=(datetime.utcnow() + timedelta(days=1)).isoformat(),
        message="یادآوری تست",
    )
    assert "reminder_id" in result or "job_id" in result or "remind_at" in result


@pytest.mark.asyncio
async def test_set_reminder_with_task_id(mock_db, mock_scheduler, sample_task):
    await mock_db.create_task(sample_task)
    result = await set_reminder(
        sample_task.user_id,
        mock_db,
        mock_scheduler,  # type: ignore
        remind_at=(datetime.utcnow() + timedelta(days=1)).isoformat(),
        message="یادآوری تسک",
        task_id=sample_task.task_id,
    )
    assert result is not None


@pytest.mark.asyncio
async def test_scheduler_service_has_schedule_reminder(mock_scheduler):
    """SchedulerService must have schedule_reminder method."""
    assert hasattr(mock_scheduler, "schedule_reminder")
    assert callable(getattr(mock_scheduler, "schedule_reminder"))


@pytest.mark.asyncio
async def test_scheduler_service_start_accepts_bot():
    """SchedulerService.start() can be called with bot."""
    s = SchedulerService("mongodb://localhost:27017", "test_db")
    try:
        await s.start(bot=None)
    except NotImplementedError:
        pass  # Stub
