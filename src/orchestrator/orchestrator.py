"""Main ReAct loop: Planner → Executor → Observer."""
from typing import Any

from src.db.database import Database
from src.llm.client import LLMClient


class Orchestrator:
    """Runs the ReAct loop. Makes ZERO decisions about meaning — LLM decides."""

    def __init__(self, db: Database, llm: LLMClient, scheduler: Any | None = None):
        self.db = db
        self.llm = llm
        self.scheduler = scheduler

    async def handle_message(self, user_id: str, message: str) -> str:
        """Main entry point. One user message → one bot response."""
        raise NotImplementedError
