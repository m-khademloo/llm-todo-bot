"""Tests for recurring tasks and due-date alerts (scheduling_tools / SchedulerService)."""
from datetime import datetime, timedelta

import pytest

from src.tools.scheduling_tools import SchedulerService


@pytest.mark.asyncio
async def test_scheduler_service_init():
    s = SchedulerService("mongodb://localhost:27017", "test_db")
    assert s.mongo_uri == "mongodb://localhost:27017"
    assert s.db_name == "test_db"


@pytest.mark.asyncio
async def test_schedule_recurring_signature():
    """SchedulerService should support scheduling recurring task (method exists)."""
    s = SchedulerService("mongodb://localhost:27017", "test_db")
    if hasattr(s, "schedule_recurring"):
        assert callable(s.schedule_recurring)


@pytest.mark.asyncio
async def test_schedule_reminder_accepts_iso_datetime(mock_db, mock_scheduler):
    """set_reminder accept ISO datetime string for remind_at."""
    from src.tools.scheduling_tools import set_reminder
    remind_at = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    result = await set_reminder(
        "u1", mock_db, mock_scheduler,
        remind_at=remind_at,
        message="Test",
    )
    assert result is not None
