"""All tool definitions (names, params, descriptions)."""
from typing import Any

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_current_datetime": {
        "description": "Get the current date and time in the user's timezone.",
        "parameters": {},
        "side_effects": False,
    },
    "get_user_tasks": {
        "description": "Fetch the user's tasks with optional filters.",
        "parameters": {
            "status": "str | null",
            "category": "str | null",
            "due_date_from": "str | null",
            "due_date_to": "str | null",
            "search_text": "str | null",
            "sort_by": "str",
            "limit": "int",
        },
        "side_effects": False,
    },
    "create_task": {
        "description": "Create a new task.",
        "parameters": {
            "title": "str",
            "description": "str | null",
            "due_date": "str | null",
            "category": "str",
            "estimated_time_minutes": "int | null",
            "priority": "int",
            "reminder_at": "str | null",
            "recurrence_pattern": "str | null",
        },
        "side_effects": True,
    },
    "update_task": {
        "description": "Update an existing task.",
        "parameters": {"task_id": "str", "updates": "dict"},
        "side_effects": True,
    },
    "complete_task": {
        "description": "Mark a task as done.",
        "parameters": {"task_id": "str"},
        "side_effects": True,
    },
    "request_task_deletion": {
        "description": "Request task deletion (triggers confirmation).",
        "parameters": {"task_id": "str"},
        "side_effects": True,
    },
    "calculate_priority": {
        "description": "Calculate priority (1-5) for a task.",
        "parameters": {
            "title": "str",
            "category": "str",
            "due_date": "str | null",
            "existing_task_count_by_priority": "dict | null",
        },
        "side_effects": False,
    },
    "get_user_config": {
        "description": "Get user preferences.",
        "parameters": {},
        "side_effects": False,
    },
    "update_user_config": {
        "description": "Update a user setting.",
        "parameters": {"key": "str", "value": "Any"},
        "side_effects": True,
    },
    "set_reminder": {
        "description": "Set a one-time reminder.",
        "parameters": {"remind_at": "str", "message": "str", "task_id": "str | null"},
        "side_effects": True,
    },
    "ask_user": {
        "description": "Ask the user a question and stop. Next message resumes.",
        "parameters": {"question": "str", "context": "str"},
        "side_effects": True,
    },
}
