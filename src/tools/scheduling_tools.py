"""set_reminder, recurring task management."""
from datetime import datetime
from typing import Any


async def set_reminder(
    user_id: str,
    db: Any,
    scheduler: Any,
    remind_at: str,
    message: str,
    task_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Set a one-time reminder."""
    try:
        at = datetime.fromisoformat(remind_at.replace("Z", "+00:00"))
    except Exception:
        return {"error": "Invalid remind_at datetime", "reminder_id": None}
    job_id = await scheduler.schedule_reminder(
        user_id=user_id,
        task_id=task_id,
        remind_at=at,
        message=message,
    )
    if hasattr(job_id, "__await__"):
        job_id = await job_id
    return {"reminder_id": job_id, "job_id": job_id, "remind_at": remind_at}


class SchedulerService:
    """Manages scheduled jobs (reminders, recurring, due-date alerts)."""

    def __init__(self, mongo_uri: str, db_name: str, bot: Any = None):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.bot = bot

    async def start(self, bot: Any = None) -> None:
        """Start the scheduler."""
        if bot is not None:
            self.bot = bot
