"""FSM state persistence + ReAct loop state save/resume."""
from typing import Any

from src.db.database import Database


class StateManager:
    """Manages conversation context save/resume for ReAct loop."""

    def __init__(self, db: Database):
        self.db = db

    async def get_saved_context(self, user_id: str) -> dict | None:
        """Load saved ReAct messages for user."""
        return await self.db.get_conversation_context(user_id)

    async def save_context(self, user_id: str, messages: list[dict]) -> bool:
        """Save ReAct messages when pausing (e.g. ask_user)."""
        return await self.db.save_conversation_context(user_id, messages)

    async def clear_context(self, user_id: str) -> bool:
        """Clear saved context (e.g. on /start or when loop finishes)."""
        return await self.db.clear_conversation_context(user_id)
