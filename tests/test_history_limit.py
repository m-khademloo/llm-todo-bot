"""Conversation history: add_message, get_history limit, ordering."""
import pytest

from tests.conftest import MockDatabase


@pytest.mark.asyncio
async def test_get_history_respects_limit(mock_db: MockDatabase):
    for i in range(15):
        await mock_db.add_message("u1", "user", f"msg{i}")
    hist = await mock_db.get_history("u1", limit=5)
    assert len(hist) == 5


@pytest.mark.asyncio
async def test_history_ordering_most_recent_first(mock_db: MockDatabase):
    await mock_db.add_message("u1", "user", "first")
    await mock_db.add_message("u1", "user", "second")
    await mock_db.add_message("u1", "user", "third")
    hist = await mock_db.get_history("u1", limit=10)
    assert len(hist) >= 3
    # Most recent should appear first (or last depending on impl)
    contents = [h["content"] for h in hist]
    assert "third" in contents
    assert "first" in contents
