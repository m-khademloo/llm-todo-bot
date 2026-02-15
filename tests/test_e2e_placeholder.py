"""E2E test placeholders: run with real LLM + test MongoDB (marked e2e, skip by default)."""
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_task_lifecycle():
    """Create → query → complete → query (empty). Uses real LLM and test DB."""
    pytest.skip("E2E: requires real LLM and MongoDB. Run with pytest -m e2e when available.")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_create_task_with_follow_up_questions():
    """Multi-turn: create task with ask_user for date."""
    pytest.skip("E2E: multi-turn create task.")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_delete_with_confirmation():
    """User asks delete → bot asks confirm → user says yes → task deleted."""
    pytest.skip("E2E: delete with confirmation.")
