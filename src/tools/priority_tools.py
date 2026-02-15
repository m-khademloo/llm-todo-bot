"""calculate_priority (sub-agent: uses LLM internally)."""
from typing import Any


async def calculate_priority(
    user_id: str,
    db: Any,
    llm: Any,
    title: str,
    category: str,
    due_date: str | None = None,
    existing_task_count_by_priority: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Calculate priority 1-5 for a task. Uses LLM as sub-agent."""
    raise NotImplementedError
