"""Executes tool calls safely (the Python side)."""
from typing import Any

from src.db.database import Database


class ToolExecutor:
    """Executes tool calls safely. Every tool is a Python function."""

    def __init__(self, db: Database, llm: Any = None, scheduler: Any = None):
        self.db = db
        self.llm = llm
        self.scheduler = scheduler

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name. Returns result dict."""
        raise NotImplementedError
