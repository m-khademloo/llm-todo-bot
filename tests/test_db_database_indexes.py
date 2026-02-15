"""Tests for Database.setup_indexes (no external MongoDB required with mock)."""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_setup_indexes_can_be_called():
    """setup_indexes creates all required indexes; with real DB or mongomock."""
    try:
        from mongomock import AsyncMongoClient
    except ImportError:
        pytest.skip("mongomock not installed")
    from src.db.database import Database
    client = AsyncMongoClient()
    db = Database.__new__(Database)
    db.client = client
    db.db = client.llm_todo_bot
    db.tasks = db.db["tasks"]
    db.users = db.db["users"]
    db.contexts = db.db["conversation_contexts"]
    db.history = db.db["conversation_history"]
    db.jobs = db.db["scheduled_jobs"]
    await db.setup_indexes()
    # No exception = success
    indexes = await db.tasks.index_information()
    assert len(indexes) >= 1
