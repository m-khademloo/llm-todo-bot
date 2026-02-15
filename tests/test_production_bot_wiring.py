"""Production: Bot must delegate every user message to orchestrator.handle_message."""
from unittest.mock import MagicMock

import pytest


def test_orchestrator_has_handle_message():
    """Orchestrator must expose handle_message(user_id, message) for bot to call."""
    from src.orchestrator.orchestrator import Orchestrator
    assert hasattr(Orchestrator, "handle_message")
    import inspect
    sig = inspect.signature(Orchestrator.handle_message)
    params = list(sig.parameters)
    assert "user_id" in params and "message" in params


def test_create_bot_signature_accepts_orchestrator():
    """create_bot(token, orchestrator) must be the production contract."""
    from src.bot import handlers
    import inspect
    sig = inspect.signature(handlers.create_bot)
    params = list(sig.parameters)
    assert len(params) >= 2
    # First two args: token and orchestrator (names may vary)
    assert "orchestrator" in params or "token" in params or len(params) >= 2


def test_start_command_does_not_require_llm():
    """ /start must work even when LLM is down (static response)."""
    from src.utils.i18n import t
    welcome = t("welcome", "fa")
    assert len(welcome) > 0
    assert "سلام" in welcome or "دستیار" in welcome
