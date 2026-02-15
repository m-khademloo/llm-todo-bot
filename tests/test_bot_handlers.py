"""Tests for bot handlers: create_bot, /start handling."""
from unittest.mock import MagicMock

import pytest

from src.bot import handlers


def test_create_bot_returns_application():
    app = handlers.create_bot("dummy_token", MagicMock())
    from telegram.ext import Application
    assert isinstance(app, Application)


def test_create_bot_accepts_token_and_orchestrator():
    """create_bot(token, orchestrator) signature."""
    import inspect
    sig = inspect.signature(handlers.create_bot)
    params = list(sig.parameters)
    assert "token" in params or "token" in str(sig)
    assert len(params) >= 2
