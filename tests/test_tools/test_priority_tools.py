"""Tests for calculate_priority sub-agent tool."""
import pytest

from src.tools import priority_tools


@pytest.mark.asyncio
async def test_calculate_priority_returns_priority_and_reasoning(mock_db, mock_llm):
    await mock_db.get_or_create_user("u1")
    result = await priority_tools.calculate_priority(
        "u1",
        mock_db,
        mock_llm,
        title="جلسه با تیم",
        category="work",
    )
    assert "priority" in result
    assert 1 <= result["priority"] <= 5
    assert "reasoning" in result or "reason" in str(result).lower()


@pytest.mark.asyncio
async def test_calculate_priority_with_due_date(mock_db, mock_llm):
    await mock_db.get_or_create_user("u1")
    result = await priority_tools.calculate_priority(
        "u1",
        mock_db,
        mock_llm,
        title="دکتر",
        category="health",
        due_date="2026-02-16T10:00:00",
    )
    assert result["priority"] >= 1
    assert result["priority"] <= 5


@pytest.mark.asyncio
async def test_calculate_priority_uses_user_priority_prompt(mock_db, mock_llm):
    await mock_db.get_or_create_user("u1")
    await mock_db.update_user_config(
        "u1", "priority_prompt", "Health first, then work"
    )
    result = await priority_tools.calculate_priority(
        "u1", mock_db, mock_llm, title="ورزش", category="health"
    )
    assert "priority" in result
