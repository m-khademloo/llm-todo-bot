"""Config: env overrides and validation."""
import os

import pytest

from src.config import Settings


def test_config_env_override(monkeypatch):
    """Settings load from environment when set."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("MONGO_URI", "mongodb://custom:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "test_db")
    s = Settings()
    assert s.TELEGRAM_BOT_TOKEN == "token123"
    assert s.MONGO_URI == "mongodb://custom:27017"
    assert s.MONGO_DB_NAME == "test_db"


def test_config_max_tasks_override(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("MAX_TASKS_PER_USER", "500")
    s = Settings()
    assert s.MAX_TASKS_PER_USER == 500


def test_config_rate_limit_override(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "20")
    s = Settings()
    assert s.RATE_LIMIT_PER_MINUTE == 20


def test_config_llm_settings(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    s = Settings()
    assert s.LLM_MODEL == "gpt-4o"
    assert s.LLM_TEMPERATURE == 0.7
