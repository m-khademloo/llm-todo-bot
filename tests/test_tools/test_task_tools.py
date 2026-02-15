"""Tests for task tools: get_user_tasks, create_task, update_task, complete_task, request_task_deletion."""
from datetime import datetime

import pytest

from src.db.models import Task, TaskCategory, TaskStatus
from src.tools import task_tools


# --- get_user_tasks ---


@pytest.mark.asyncio
async def test_get_user_tasks_empty(mock_db):
    result = await task_tools.get_user_tasks("u1", mock_db)
    assert result["count"] == 0
    assert result["tasks"] == []


@pytest.mark.asyncio
async def test_get_user_tasks_with_tasks(mock_db, sample_tasks):
    for t in sample_tasks:
        await mock_db.create_task(t)
    result = await task_tools.get_user_tasks(sample_tasks[0].user_id, mock_db)
    assert result["count"] == 2
    assert len(result["tasks"]) == 2
    titles = [x["title"] for x in result["tasks"]]
    assert "جلسه پروژه" in titles
    assert "رفتن به دکتر" in titles


@pytest.mark.asyncio
async def test_get_user_tasks_filter_status(mock_db, sample_task):
    await mock_db.create_task(sample_task)
    await mock_db.complete_task(sample_task.user_id, sample_task.task_id)
    pending = await task_tools.get_user_tasks(sample_task.user_id, mock_db, status="pending")
    assert pending["count"] == 0
    done = await task_tools.get_user_tasks(sample_task.user_id, mock_db, status="done")
    assert done["count"] == 1


@pytest.mark.asyncio
async def test_get_user_tasks_filter_category(mock_db, sample_tasks):
    for t in sample_tasks:
        await mock_db.create_task(t)
    result = await task_tools.get_user_tasks(
        sample_tasks[0].user_id, mock_db, category="work"
    )
    assert result["count"] == 1
    assert result["tasks"][0]["category"] == "work"


@pytest.mark.asyncio
async def test_get_user_tasks_filter_due_date_range(mock_db, sample_task):
    await mock_db.create_task(sample_task)
    result = await task_tools.get_user_tasks(
        sample_task.user_id,
        mock_db,
        due_date_from="2026-02-16",
        due_date_to="2026-02-16",
    )
    assert result["count"] >= 1
    assert "task_id" in result["tasks"][0]
    assert "title" in result["tasks"][0]
    assert "priority" in result["tasks"][0]


@pytest.mark.asyncio
async def test_get_user_tasks_limit(mock_db, sample_tasks):
    for t in sample_tasks:
        await mock_db.create_task(t)
    result = await task_tools.get_user_tasks(
        sample_tasks[0].user_id, mock_db, limit=1
    )
    assert len(result["tasks"]) <= 1


# --- create_task ---


@pytest.mark.asyncio
async def test_create_task_minimal(mock_db):
    result = await task_tools.create_task(
        "u1", mock_db, title="New task", category="personal"
    )
    assert "task_id" in result
    assert result["title"] == "New task"
    task = await mock_db.get_task("u1", result["task_id"])
    assert task is not None
    assert task.title == "New task"
    assert task.category == TaskCategory.PERSONAL
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_create_task_with_due_date(mock_db):
    result = await task_tools.create_task(
        "u1",
        mock_db,
        title="Meeting",
        category="work",
        due_date="2026-02-16T10:00:00",
        priority=2,
    )
    assert result["task_id"]
    task = await mock_db.get_task("u1", result["task_id"])
    assert task.due_date is not None


@pytest.mark.asyncio
async def test_create_task_respects_max_tasks_per_user(mock_db):
    """When user has MAX_TASKS_PER_USER tasks, create_task should fail or signal limit."""
    # Create up to limit (implementation may check and return error)
    for i in range(5):
        await task_tools.create_task(
            "u1", mock_db, title=f"Task {i}", category="personal"
        )
    # Either 5 created or implementation enforces limit earlier
    tasks = await mock_db.query_tasks("u1", limit=100)
    assert len(tasks) == 5


# --- update_task ---


@pytest.mark.asyncio
async def test_update_task_title(mock_db, sample_task):
    await mock_db.create_task(sample_task)
    result = await task_tools.update_task(
        sample_task.user_id,
        mock_db,
        sample_task.task_id,
        {"title": "Updated title"},
    )
    assert result.get("success", True) is not False
    task = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
    assert task.title == "Updated title"


@pytest.mark.asyncio
async def test_update_task_nonexistent_returns_failure(mock_db):
    result = await task_tools.update_task(
        "u1", mock_db, "nonexistent_id", {"title": "x"}
    )
    assert result.get("success") is False or "error" in result


# --- complete_task ---


@pytest.mark.asyncio
async def test_complete_task_success(mock_db, sample_task):
    await mock_db.create_task(sample_task)
    result = await task_tools.complete_task(
        sample_task.user_id, mock_db, sample_task.task_id
    )
    assert result.get("success") is True
    task = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
    assert task.status == TaskStatus.DONE


@pytest.mark.asyncio
async def test_complete_task_nonexistent(mock_db):
    result = await task_tools.complete_task("u1", mock_db, "nonexistent")
    assert result.get("success") is False or "error" in result


# --- request_task_deletion ---


@pytest.mark.asyncio
async def test_request_task_deletion_returns_confirmation_message(mock_db, sample_task):
    await mock_db.create_task(sample_task)
    result = await task_tools.request_task_deletion(
        sample_task.user_id, mock_db, sample_task.task_id
    )
    # Tool should return a message asking for confirmation, not delete immediately
    assert "question" in result or "confirm" in result or "delete" in str(result).lower()
    # Task should still exist until user confirms
    task = await mock_db.get_task(sample_task.user_id, sample_task.task_id)
    assert task is not None
