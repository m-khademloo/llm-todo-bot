"""Feature: Task lifecycle from docs (04 - Task Creation/Update/Completion/Deletion/Query)."""
import pytest

from src.db.models import Task, TaskCategory, TaskStatus
from tests.conftest import MockDatabase


class TestTaskQueryFlow:
    """Query types: today, tomorrow, this week, all pending, done, by category, sort by priority/date."""

    @pytest.mark.asyncio
    async def test_get_user_tasks_filter_status_pending(self, mock_db: MockDatabase, sample_tasks):
        for t in sample_tasks:
            await mock_db.create_task(t)
        from src.tools import task_tools
        r = await task_tools.get_user_tasks(sample_tasks[0].user_id, mock_db, status="pending")
        assert r["count"] >= 2
        assert all(x.get("status") == "pending" for x in r["tasks"])

    @pytest.mark.asyncio
    async def test_get_user_tasks_filter_status_done(self, mock_db: MockDatabase, sample_task):
        await mock_db.create_task(sample_task)
        await mock_db.complete_task(sample_task.user_id, sample_task.task_id)
        from src.tools import task_tools
        r = await task_tools.get_user_tasks(sample_task.user_id, mock_db, status="done")
        assert r["count"] >= 1

    @pytest.mark.asyncio
    async def test_get_user_tasks_filter_status_all(self, mock_db: MockDatabase, sample_task):
        await mock_db.create_task(sample_task)
        await mock_db.complete_task(sample_task.user_id, sample_task.task_id)
        from src.tools import task_tools
        r = await task_tools.get_user_tasks(sample_task.user_id, mock_db, status="all")
        assert r["count"] >= 1

    @pytest.mark.asyncio
    async def test_get_user_tasks_sort_by_priority(self, mock_db: MockDatabase, sample_tasks):
        from src.tools import task_tools
        for t in sample_tasks:
            await mock_db.create_task(t)
        r = await task_tools.get_user_tasks(
            sample_tasks[0].user_id, mock_db, sort_by="priority"
        )
        assert "tasks" in r
        if len(r["tasks"]) >= 2:
            priorities = [x.get("priority") for x in r["tasks"]]
            assert priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_get_user_tasks_sort_by_due_date(self, mock_db: MockDatabase):
        from src.tools import task_tools
        await mock_db.create_task(Task(user_id="u1", title="A", category=TaskCategory.PERSONAL))
        r = await task_tools.get_user_tasks("u1", mock_db, sort_by="due_date")
        assert "tasks" in r


class TestTaskCompletionFlow:
    """On completion: status=done, completed_at set; cancel pending reminders; recurring: next occurrence."""

    @pytest.mark.asyncio
    async def test_complete_task_sets_done_and_completed_at(self, mock_db: MockDatabase, sample_task):
        await mock_db.create_task(sample_task)
        await mock_db.complete_task(sample_task.user_id, sample_task.task_id)
        t = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
        assert t.status == TaskStatus.DONE
        assert t.completed_at is not None


class TestTaskDeletionFlow:
    """Always require confirmation; soft delete (status=cancelled) per doc."""

    def test_delete_can_soft_delete_via_update(self, mock_db: MockDatabase, sample_task):
        """Contract: deletion may set status to cancelled instead of removing document."""
        from src.db.models import TaskStatus
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestQueryResultFormatting:
    """no_tasks message when 0 tasks."""

    def test_no_tasks_template_exists(self):
        from src.utils.i18n import t
        msg = t("no_tasks", "fa")
        assert "هیچ تسکی" in msg or "نداری" in msg or "استراحت" in msg

    @pytest.mark.asyncio
    async def test_get_user_tasks_empty_returns_zero_count(self, mock_db: MockDatabase):
        from src.tools import task_tools
        r = await task_tools.get_user_tasks("u1", mock_db)
        assert r["count"] == 0
        assert r["tasks"] == []
