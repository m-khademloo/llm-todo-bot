"""User isolation: one user must never see or modify another user's data."""
import pytest

from src.db.models import Task, TaskCategory
from tests.conftest import MockDatabase


@pytest.mark.asyncio
async def test_get_task_returns_none_for_other_user(mock_db: MockDatabase):
    t = Task(user_id="user_a", title="Secret", category=TaskCategory.PERSONAL)
    await mock_db.create_task(t)
    got = await mock_db.get_task("user_b", t.task_id)
    assert got is None


@pytest.mark.asyncio
async def test_update_task_other_user_fails(mock_db: MockDatabase):
    t = Task(user_id="user_a", title="Task", category=TaskCategory.PERSONAL)
    await mock_db.create_task(t)
    ok = await mock_db.update_task("user_b", t.task_id, {"title": "Hacked"})
    assert ok is False
    task = await mock_db.get_task("user_a", t.task_id)
    assert task.title == "Task"


@pytest.mark.asyncio
async def test_delete_task_other_user_fails(mock_db: MockDatabase):
    t = Task(user_id="user_a", title="Task", category=TaskCategory.PERSONAL)
    await mock_db.create_task(t)
    ok = await mock_db.delete_task("user_b", t.task_id)
    assert ok is False
    task = await mock_db.get_task("user_a", t.task_id)
    assert task is not None


@pytest.mark.asyncio
async def test_query_tasks_only_returns_own(mock_db: MockDatabase):
    await mock_db.create_task(Task(user_id="user_a", title="A", category=TaskCategory.PERSONAL))
    await mock_db.create_task(Task(user_id="user_b", title="B", category=TaskCategory.PERSONAL))
    from src.db.models import TaskFilter
    tasks_a = await mock_db.query_tasks("user_a", limit=10)
    tasks_b = await mock_db.query_tasks("user_b", limit=10)
    assert len(tasks_a) == 1
    assert len(tasks_b) == 1
    assert tasks_a[0].title == "A"
    assert tasks_b[0].title == "B"


@pytest.mark.asyncio
async def test_conversation_context_per_user(mock_db: MockDatabase):
    await mock_db.save_conversation_context("user_a", [{"role": "user", "content": "A"}])
    await mock_db.save_conversation_context("user_b", [{"role": "user", "content": "B"}])
    ctx_a = await mock_db.get_conversation_context("user_a")
    ctx_b = await mock_db.get_conversation_context("user_b")
    assert ctx_a["messages"][0]["content"] == "A"
    assert ctx_b["messages"][0]["content"] == "B"
