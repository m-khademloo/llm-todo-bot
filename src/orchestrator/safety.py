"""Confirmation logic, user isolation, rate limits."""
from collections import defaultdict
from time import time
from typing import Any

DESTRUCTIVE_TOOLS = {"request_task_deletion", "delete_task"}


class SafetyLayer:
    """Enforces confirmation for destructive actions, user isolation, rate limits."""

    def __init__(self, rate_limit_per_minute: int = 10):
        self.rate_limit_per_minute = rate_limit_per_minute
        self._messages: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, user_id: str) -> bool:
        """Return True if user is within rate limit."""
        now = time()
        window_start = now - 60
        self._messages[user_id] = [t for t in self._messages[user_id] if t > window_start]
        return len(self._messages[user_id]) < self.rate_limit_per_minute

    def requires_confirmation(self, tool_name: str) -> bool:
        """Return True if tool requires user confirmation before execution."""
        return tool_name in DESTRUCTIVE_TOOLS

    def record_message(self, user_id: str) -> None:
        """Record a message for rate limiting."""
        self._messages[user_id].append(time())
