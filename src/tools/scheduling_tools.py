"""set_reminder, recurring task management."""
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
    raise NotImplementedError


class SchedulerService:
    """Manages scheduled jobs (reminders, recurring, due-date alerts)."""

    def __init__(self, mongo_uri: str, db_name: str, bot: Any = None):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.bot = bot

    async def start(self, bot: Any = None) -> None:
        """Start the scheduler."""
        raise NotImplementedError

    async def schedule_reminder(
        self,
        user_id: str,
        task_id: str | None,
        remind_at: Any,
        message: str,
    ) -> str:
        """Schedule a one-shot reminder. Returns job_id."""
        raise NotImplementedError
