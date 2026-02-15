"""Tests for ask_user tool (pause/resume ReAct loop)."""
import pytest

from src.tools import conversation_tools


@pytest.mark.asyncio
async def test_ask_user_returns_question_and_waiting_flag():
    result = await conversation_tools.ask_user(
        "u1",
        question="کی باید بری؟",
        context="gathering_create",
    )
    assert result.get("waiting_for_response") is True
    assert result.get("question") == "کی باید بری؟"
    assert "context" in result or "gathering_create" in str(result)


@pytest.mark.asyncio
async def test_ask_user_empty_question_still_returns_structure():
    result = await conversation_tools.ask_user("u1", question="", context="")
    assert "waiting_for_response" in result
    assert "question" in result
