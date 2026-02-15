"""Tests for config module."""
import os

import pytest

from src.config import Settings


class TestSettings:
    def test_defaults(self):
        # Without .env, use defaults where optional
        s = Settings(TELEGRAM_BOT_TOKEN="dummy")
        assert s.MONGO_URI == "mongodb://localhost:27017"
        assert s.MONGO_DB_NAME == "llm_todo_bot"
        assert s.LLM_MODEL == "ollama/deepseek-r1:14b"
        assert s.LLM_TEMPERATURE == 0.3
        assert s.MAX_TASKS_PER_USER == 200
        assert s.MAX_TOOL_CALLS_PER_MESSAGE == 10
        assert s.RATE_LIMIT_PER_MINUTE == 10
        assert s.MAX_GATHER_TURNS == 3

    def test_telegram_token_can_be_set(self):
        s = Settings(TELEGRAM_BOT_TOKEN="secret123")
        assert s.TELEGRAM_BOT_TOKEN == "secret123"
