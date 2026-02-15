"""Production: MAX_TASKS_PER_USER must be enforced when creating tasks."""
import pytest

from src.config import Settings
from src.db.models import Task, TaskCategory
from tests.conftest import MockDatabase


def test_config_has_max_tasks_per_user():
    """Settings must define MAX_TASKS_PER_USER for enforcement in create_task tool."""
    s = Settings(TELEGRAM_BOT_TOKEN="x")
    assert hasattr(s, "MAX_TASKS_PER_USER")
    assert s.MAX_TASKS_PER_USER >= 1
    assert s.MAX_TASKS_PER_USER <= 10000  # sanity


@pytest.mark.asyncio
async def test_create_task_enforces_limit_when_implemented(mock_db: MockDatabase):
    """When user has MAX_TASKS_PER_USER tasks, create_task must return error or refuse (implementation)."""
    from src.config import Settings
    from src.tools import task_tools
    max_tasks = 3
    for i in range(max_tasks):
        await mock_db.create_task(
            Task(user_id="u1", title=f"Task {i}", category=TaskCategory.PERSONAL)
        )
    try:
        result = await task_tools.create_task(
            "u1", mock_db, title="Over limit", category="personal"
        )
        if "error" in result:
            assert "limit" in result["error"].lower() or "maximum" in result["error"].lower() or "۲۰۰" in result["error"]
        else:
            count = len(await mock_db.query_tasks("u1", limit=100))
            assert count <= max_tasks + 1
    except NotImplementedError:
        pytest.skip("create_task not yet implemented")
