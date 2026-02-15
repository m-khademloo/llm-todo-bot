"""Shared fixtures: MockLLM, MockDB, sample data."""
import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models import (
    Task,
    TaskCategory,
    TaskStatus,
    User,
    ReminderConfig,
    RecurrenceConfig,
    QuietHoursConfig,
    TaskFilter,
    ScheduledJob,
)
from src.db.database import Database


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# --- Sample data ---


@pytest.fixture
def sample_user() -> User:
    return User(
        user_id="test_user_123",
        first_name="Test",
        language="fa",
        timezone="Asia/Tehran",
    )


@pytest.fixture
def sample_task(sample_user: User) -> Task:
    return Task(
        task_id="task_abc",
        user_id=sample_user.user_id,
        title="جلسه با تیم فنی",
        category=TaskCategory.WORK,
        status=TaskStatus.PENDING,
        priority=2,
        due_date=datetime(2026, 2, 16, 10, 0, 0),
        estimated_time_minutes=60,
    )


@pytest.fixture
def sample_tasks(sample_user: User) -> list[Task]:
    return [
        Task(
            task_id="t1",
            user_id=sample_user.user_id,
            title="جلسه پروژه",
            category=TaskCategory.WORK,
            priority=1,
            status=TaskStatus.PENDING,
        ),
        Task(
            task_id="t2",
            user_id=sample_user.user_id,
            title="رفتن به دکتر",
            category=TaskCategory.HEALTH,
            priority=2,
            status=TaskStatus.PENDING,
        ),
    ]


# --- Mock Database ---


class MockDatabase:
    """In-memory mock for Database. All methods are async and scoped by user_id."""

    def __init__(self):
        self._tasks: dict[str, list[dict]] = {}
        self._users: dict[str, dict] = {}
        self._contexts: dict[str, dict] = {}
        self._history: list[dict] = []
        self._jobs: list[dict] = []

    def _user_tasks(self, user_id: str) -> list[dict]:
        if user_id not in self._tasks:
            self._tasks[user_id] = []
        return self._tasks[user_id]

    async def create_task(self, task: Task) -> str:
        doc = task.model_dump(mode="json")
        self._user_tasks(task.user_id).append(doc)
        return task.task_id

    async def get_task(self, user_id: str, task_id: str) -> Task | None:
        for t in self._user_tasks(user_id):
            if t.get("task_id") == task_id:
                return Task.model_validate(t)
        return None

    async def update_task(self, user_id: str, task_id: str, updates: dict) -> bool:
        for t in self._user_tasks(user_id):
            if t.get("task_id") == task_id:
                t.update(updates)
                return True
        return False

    async def delete_task(self, user_id: str, task_id: str) -> bool:
        tasks = self._user_tasks(user_id)
        for i, t in enumerate(tasks):
            if t.get("task_id") == task_id:
                tasks.pop(i)
                return True
        return False

    async def complete_task(self, user_id: str, task_id: str) -> bool:
        return await self.update_task(
            user_id, task_id, {"status": "done", "completed_at": datetime.utcnow()}
        )

    async def query_tasks(
        self,
        user_id: str,
        filters: TaskFilter | None = None,
        limit: int = 20,
    ) -> list[Task]:
        tasks = self._user_tasks(user_id)
        result = []
        for t in tasks:
            if filters and filters.status and t.get("status") != filters.status:
                continue
            if filters and filters.category and t.get("category") != filters.category:
                continue
            result.append(Task.model_validate(t))
            if len(result) >= limit:
                break
        return result

    async def get_or_create_user(self, user_id: str, **info: Any) -> User:
        if user_id in self._users:
            return User.model_validate(self._users[user_id])
        user = User(user_id=user_id, **info)
        self._users[user_id] = user.model_dump(mode="json")
        return user

    async def get_user(self, user_id: str) -> User | None:
        if user_id not in self._users:
            return None
        return User.model_validate(self._users[user_id])

    async def update_user_config(self, user_id: str, key: str, value: Any) -> bool:
        if user_id not in self._users:
            return False
        self._users[user_id][key] = value
        return True

    async def get_conversation_context(self, user_id: str) -> dict | None:
        return self._contexts.get(user_id)

    async def save_conversation_context(self, user_id: str, messages: list[dict]) -> bool:
        self._contexts[user_id] = {"user_id": user_id, "messages": messages}
        return True

    async def clear_conversation_context(self, user_id: str) -> bool:
        if user_id in self._contexts:
            del self._contexts[user_id]
            return True
        return True

    async def add_message(
        self, user_id: str, role: str, content: str, **metadata: Any
    ) -> None:
        self._history.append(
            {"user_id": user_id, "role": role, "content": content, "metadata": metadata}
        )

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict]:
        user_hist = [h for h in self._history if h["user_id"] == user_id]
        return user_hist[-limit:][::-1]

    async def create_job(self, job: ScheduledJob) -> str:
        self._jobs.append(job.model_dump(mode="json"))
        return job.job_id

    async def get_pending_jobs(self, before: datetime) -> list[ScheduledJob]:
        return [
            ScheduledJob.model_validate(j)
            for j in self._jobs
            if j.get("status") == "pending" and j.get("trigger_at", datetime.max) <= before
        ]

    async def mark_job_fired(self, job_id: str) -> bool:
        for j in self._jobs:
            if j.get("job_id") == job_id:
                j["status"] = "fired"
                return True
        return False


@pytest.fixture
def mock_db() -> MockDatabase:
    return MockDatabase()


# --- Mock LLM ---


class MockLLMResponse:
    def __init__(self, content: str = "", tool_calls: list[Any] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.call_with_tools = AsyncMock(return_value=MockLLMResponse(content="OK"))
    llm.call_simple = AsyncMock(return_value='{"priority": 3, "reasoning": "test"}')
    return llm


# --- Mock Scheduler ---


@pytest.fixture
def mock_scheduler() -> MagicMock:
    s = MagicMock()
    s.start = AsyncMock(return_value=None)
    s.schedule_reminder = AsyncMock(return_value="job_123")
    s.schedule_recurring = AsyncMock(return_value="recur_123")
    return s


# --- Real DB for integration (optional) ---


@pytest.fixture
async def real_db():
    """Use real Database with in-memory MongoDB (e.g. mongomock) if available."""
    pytest.importorskip("mongomock")
    from mongomock import AsyncMongoClient
    client = AsyncMongoClient()
    db = Database.__new__(Database)
    db.client = client
    db.db = client.llm_todo_bot
    db.tasks = db.db["tasks"]
    db.users = db.db["users"]
    db.contexts = db.db["conversation_contexts"]
    db.history = db.db["conversation_history"]
    db.jobs = db.db["scheduled_jobs"]
    yield db
