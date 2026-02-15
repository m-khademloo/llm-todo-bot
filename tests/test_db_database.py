"""Tests for Database layer: CRUD, user isolation, context, history, jobs."""
from datetime import datetime

import pytest

from src.db.models import Task, TaskCategory, TaskStatus, User, TaskFilter, ScheduledJob
from src.db.database import Database
from tests.conftest import MockDatabase


class TestDatabaseWithMock:
    """Tests using MockDatabase (no real MongoDB)."""

    @pytest.mark.asyncio
    async def test_create_and_get_task(self, mock_db: MockDatabase, sample_task: Task):
        tid = await mock_db.create_task(sample_task)
        assert tid == sample_task.task_id
        got = await mock_db.get_task(sample_task.user_id, tid)
        assert got is not None
        assert got.title == sample_task.title
        assert got.category == sample_task.category

    @pytest.mark.asyncio
    async def test_get_task_wrong_user_returns_none(self, mock_db: MockDatabase, sample_task: Task):
        await mock_db.create_task(sample_task)
        got = await mock_db.get_task("other_user", sample_task.task_id)
        assert got is None

    @pytest.mark.asyncio
    async def test_update_task(self, mock_db: MockDatabase, sample_task: Task):
        await mock_db.create_task(sample_task)
        ok = await mock_db.update_task(
            sample_task.user_id,
            sample_task.task_id,
            {"title": "Updated title", "priority": 1},
        )
        assert ok is True
        got = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
        assert got.title == "Updated title"
        assert got.priority == 1

    @pytest.mark.asyncio
    async def test_complete_task(self, mock_db: MockDatabase, sample_task: Task):
        await mock_db.create_task(sample_task)
        ok = await mock_db.complete_task(sample_task.user_id, sample_task.task_id)
        assert ok is True
        got = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
        assert got.status == TaskStatus.DONE
        assert got.completed_at is not None

    @pytest.mark.asyncio
    async def test_delete_task(self, mock_db: MockDatabase, sample_task: Task):
        await mock_db.create_task(sample_task)
        ok = await mock_db.delete_task(sample_task.user_id, sample_task.task_id)
        assert ok is True
        got = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
        assert got is None

    @pytest.mark.asyncio
    async def test_query_tasks_by_status(self, mock_db: MockDatabase, sample_tasks: list[Task]):
        for t in sample_tasks:
            await mock_db.create_task(t)
        one_done = Task(
            task_id="t3",
            user_id=sample_tasks[0].user_id,
            title="Done task",
            status=TaskStatus.DONE,
        )
        await mock_db.create_task(one_done)
        pending = await mock_db.query_tasks(
            sample_tasks[0].user_id, TaskFilter(status="pending")
        )
        assert len(pending) == 2
        done = await mock_db.query_tasks(
            sample_tasks[0].user_id, TaskFilter(status="done")
        )
        assert len(done) == 1

    @pytest.mark.asyncio
    async def test_get_or_create_user(self, mock_db: MockDatabase):
        u = await mock_db.get_or_create_user("u1", first_name="Test")
        assert u.user_id == "u1"
        assert u.first_name == "Test"
        u2 = await mock_db.get_or_create_user("u1")
        assert u2.user_id == "u1"

    @pytest.mark.asyncio
    async def test_update_user_config(self, mock_db: MockDatabase):
        await mock_db.get_or_create_user("u1")
        ok = await mock_db.update_user_config("u1", "language", "en")
        assert ok is True
        u = await mock_db.get_user("u1")
        assert u.language == "en"

    @pytest.mark.asyncio
    async def test_conversation_context_save_and_get(self, mock_db: MockDatabase):
        messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        await mock_db.save_conversation_context("u1", messages)
        ctx = await mock_db.get_conversation_context("u1")
        assert ctx is not None
        assert "messages" in ctx
        assert len(ctx["messages"]) == 2

    @pytest.mark.asyncio
    async def test_conversation_context_clear(self, mock_db: MockDatabase):
        await mock_db.save_conversation_context("u1", [{"role": "user", "content": "x"}])
        await mock_db.clear_conversation_context("u1")
        ctx = await mock_db.get_conversation_context("u1")
        assert ctx is None

    @pytest.mark.asyncio
    async def test_add_and_get_history(self, mock_db: MockDatabase):
        await mock_db.add_message("u1", "user", "سلام")
        await mock_db.add_message("u1", "assistant", "سلام!")
        hist = await mock_db.get_history("u1", limit=10)
        assert len(hist) == 2

    @pytest.mark.asyncio
    async def test_create_job_and_mark_fired(self, mock_db: MockDatabase):
        job = ScheduledJob(
            job_id="j1",
            user_id="u1",
            job_type="reminder",
            trigger_at=datetime(2026, 2, 16, 9, 0),
            message="یادآوری",
        )
        jid = await mock_db.create_job(job)
        assert jid == "j1"
        ok = await mock_db.mark_job_fired("j1")
        assert ok is True
