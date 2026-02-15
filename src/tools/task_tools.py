"""get_user_tasks, create_task, update_task, complete_task, request_task_deletion."""
from datetime import datetime, time
from typing import Any

from src.config import Settings
from src.db.models import Task, TaskCategory, TaskStatus, TaskFilter


def _parse_date(s: str | None, end_of_day: bool = False) -> datetime | None:
    if not s:
        return None
    s = s.replace("Z", "+00:00").strip()
    if len(s) <= 10:
        d = datetime.fromisoformat(s).date()
        return datetime.combine(d, time(23, 59, 59, 999999)) if end_of_day else datetime.combine(d, time(0, 0, 0))
    return datetime.fromisoformat(s)


async def get_user_tasks(
    user_id: str,
    db: Any,
    status: str = "pending",
    category: str | None = None,
    due_date_from: str | None = None,
    due_date_to: str | None = None,
    search_text: str | None = None,
    sort_by: str = "priority",
    limit: int = 20,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch user's tasks with optional filters."""
    due_from = _parse_date(due_date_from, end_of_day=False) if due_date_from else None
    due_to = _parse_date(due_date_to, end_of_day=True) if due_date_to else None
    filters = TaskFilter(
        status=None if status == "all" else status,
        category=category,
        due_date_from=due_from,
        due_date_to=due_to,
    )
    tasks = await db.query_tasks(user_id, filters=filters, limit=limit, sort_by=sort_by)
    return {
        "count": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "title": t.title,
                "description": t.description,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "priority": t.priority,
                "category": t.category.value if hasattr(t.category, "value") else t.category,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "estimated_time_minutes": t.estimated_time_minutes,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ],
    }


async def create_task(
    user_id: str,
    db: Any,
    title: str,
    category: str,
    priority: int = 3,
    description: str | None = None,
    due_date: str | None = None,
    estimated_time_minutes: int | None = None,
    reminder_at: str | None = None,
    recurrence_pattern: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a new task."""
    settings = Settings()
    current = await db.query_tasks(user_id, limit=settings.MAX_TASKS_PER_USER + 1)
    if len(current) >= settings.MAX_TASKS_PER_USER:
        return {
            "error": f"Maximum tasks per user ({settings.MAX_TASKS_PER_USER}) reached.",
        }
    cat = TaskCategory(category) if category in [c.value for c in TaskCategory] else TaskCategory.PERSONAL
    task = Task(
        user_id=user_id,
        title=title,
        category=cat,
        priority=max(1, min(5, priority)),
        description=description,
        due_date=datetime.fromisoformat(due_date.replace("Z", "+00:00")) if due_date else None,
        estimated_time_minutes=estimated_time_minutes,
    )
    await db.create_task(task)
    return {"task_id": task.task_id, "title": task.title, "priority": task.priority}


async def update_task(
    user_id: str, db: Any, task_id: str, updates: dict, **kwargs: Any
) -> dict[str, Any]:
    """Update an existing task."""
    task = await db.get_task(user_id, task_id)
    if not task:
        return {"success": False, "error": "Task not found"}
    clean = {}
    for k, v in updates.items():
        if k == "due_date" and v:
            clean[k] = datetime.fromisoformat(v.replace("Z", "+00:00")) if isinstance(v, str) else v
        else:
            clean[k] = v
    ok = await db.update_task(user_id, task_id, clean)
    return {"success": ok}


async def complete_task(
    user_id: str, db: Any, task_id: str, **kwargs: Any
) -> dict[str, Any]:
    """Mark a task as done."""
    task = await db.get_task(user_id, task_id)
    if not task:
        return {"success": False, "error": "Task not found"}
    ok = await db.complete_task(user_id, task_id)
    return {"success": ok, "task_title": task.title}


async def request_task_deletion(
    user_id: str, db: Any, task_id: str, **kwargs: Any
) -> dict[str, Any]:
    """Request task deletion (confirmation required). Returns a question for the user."""
    task = await db.get_task(user_id, task_id)
    if not task:
        return {"error": "Task not found", "question": None}
    from src.utils.i18n import t
    user = await db.get_or_create_user(user_id)
    lang = user.language or "fa"
    question = f"حذف تسک «{task.title}» رو تأیید می‌کنی؟" if lang == "fa" else f"Confirm delete task «{task.title}»?"
    return {"question": question, "confirm": "yes", "task_id": task_id, "task_title": task.title}
