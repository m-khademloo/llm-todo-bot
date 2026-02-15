"""calculate_priority (sub-agent: uses LLM internally)."""
import json
import re
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
    user = await db.get_or_create_user(user_id)
    prompt = f"""Calculate priority 1-5 for this task. 1=most urgent, 5=least.
Task: {title}
Category: {category}
Due: {due_date or 'not set'}
User's priority preferences: {user.priority_prompt or 'No specific preferences.'}
Respond with JSON only: {{"priority": N, "reasoning": "..."}}"""
    try:
        result = await llm.call_simple(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        if isinstance(result, dict):
            priority = result.get("priority", 3)
            reasoning = result.get("reasoning", "")
        else:
            text = result.strip()
            match = re.search(r'\{[^{}]*"priority"\s*:\s*(\d+)[^{}]*\}', text)
            if match:
                priority = int(match.group(1))
            else:
                priority = 3
            reasoning = text[:200] if text else ""
        priority = max(1, min(5, int(priority)))
        return {"priority": priority, "reasoning": reasoning or "Default priority."}
    except Exception as e:
        return {"priority": 3, "reasoning": f"Fallback: {e}"}
