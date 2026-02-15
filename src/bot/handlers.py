"""Telegram message/command handlers → calls orchestrator."""
from typing import Any


def create_bot(token: str, orchestrator: Any) -> Any:
    """Create and return the Telegram bot application."""
    raise NotImplementedError
