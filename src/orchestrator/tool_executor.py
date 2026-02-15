"""Executes tool calls safely (the Python side)."""
from typing import Any

from src.db.database import Database
from src.tools import (
    conversation_tools,
    config_tools,
    datetime_tools,
    priority_tools,
    scheduling_tools,
    task_tools,
)


class ToolExecutor:
    """Executes tool calls safely. Every tool is a Python function."""

    def __init__(self, db: Database, llm: Any = None, scheduler: Any = None):
        self.db = db
        self.llm = llm
        self.scheduler = scheduler

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name. Returns result dict."""
        if not tool_name or not tool_name.strip():
            return {"error": "Empty tool name"}
        user_id = args.pop("_user_id", None)
        if user_id is None:
            return {"error": "Missing _user_id"}
        if tool_name not in _TOOL_FUNCS:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            fn = _TOOL_FUNCS[tool_name]
            if fn == conversation_tools.ask_user:
                return await fn(user_id=user_id, **args)
            if fn == datetime_tools.get_current_datetime:
                return await fn(user_id, self.db, **args)
            if fn == priority_tools.calculate_priority:
                return await fn(user_id, self.db, self.llm, **args)
            if fn == scheduling_tools.set_reminder:
                return await fn(user_id, self.db, self.scheduler, **args)
            return await fn(user_id, self.db, **args)
        except Exception as e:
            return {"error": f"Tool {tool_name} failed: {str(e)}"}


_TOOL_FUNCS = {
    "get_current_datetime": datetime_tools.get_current_datetime,
    "get_user_tasks": task_tools.get_user_tasks,
    "create_task": task_tools.create_task,
    "update_task": task_tools.update_task,
    "complete_task": task_tools.complete_task,
    "request_task_deletion": task_tools.request_task_deletion,
    "calculate_priority": priority_tools.calculate_priority,
    "get_user_config": config_tools.get_user_config,
    "update_user_config": config_tools.update_user_config,
    "set_reminder": scheduling_tools.set_reminder,
    "ask_user": conversation_tools.ask_user,
}
