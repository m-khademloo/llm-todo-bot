"""MongoDB connection and access layer."""
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from src.db.models import (
    Task,
    User,
    TaskFilter,
    ScheduledJob,
    SavedReActContext,
)


class Database:
    """Async MongoDB access layer."""

    def __init__(self, mongo_uri: str, db_name: str = "llm_todo_bot"):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.tasks = self.db["tasks"]
        self.users = self.db["users"]
        self.contexts = self.db["conversation_contexts"]
        self.history = self.db["conversation_history"]
        self.jobs = self.db["scheduled_jobs"]

    async def setup_indexes(self) -> None:
        """Create all indexes. Call once on startup."""
        await self.tasks.create_index([("user_id", 1), ("status", 1)])
        await self.tasks.create_index([("user_id", 1), ("due_date", 1)])
        await self.tasks.create_index([("user_id", 1), ("category", 1)])
        await self.tasks.create_index([("reminder.remind_at", 1)], sparse=True)
        await self.tasks.create_index([("recurrence.next_occurrence", 1)], sparse=True)
        await self.users.create_index("user_id", unique=True)
        await self.contexts.create_index("user_id", unique=True)
        await self.history.create_index([("user_id", 1), ("timestamp", -1)])
        # TTL: auto-delete messages older than 30 days (2592000 seconds)
        await self.history.create_index("timestamp", expireAfterSeconds=2592000)
        await self.jobs.create_index([("trigger_at", 1), ("status", 1)])
        await self.jobs.create_index("user_id")
        await self.jobs.create_index("task_id", sparse=True)

    # --- Tasks ---
    async def create_task(self, task: Task) -> str:
        doc = task.model_dump(mode="json")
        await self.tasks.insert_one(doc)
        return task.task_id

    async def get_task(self, user_id: str, task_id: str) -> Task | None:
        doc = await self.tasks.find_one({"user_id": user_id, "task_id": task_id})
        return Task.model_validate(doc) if doc else None

    async def update_task(self, user_id: str, task_id: str, updates: dict) -> bool:
        from bson import ObjectId
        for k, v in list(updates.items()):
            if hasattr(v, "isoformat"):
                updates[k] = v
        updates["updated_at"] = datetime.utcnow()
        r = await self.tasks.update_one(
            {"user_id": user_id, "task_id": task_id}, {"$set": updates}
        )
        return r.modified_count > 0

    async def delete_task(self, user_id: str, task_id: str) -> bool:
        r = await self.tasks.delete_one({"user_id": user_id, "task_id": task_id})
        return r.deleted_count > 0

    async def complete_task(self, user_id: str, task_id: str) -> bool:
        return await self.update_task(
            user_id, task_id, {"status": "done", "completed_at": datetime.utcnow()}
        )

    async def query_tasks(
        self, user_id: str, filters: TaskFilter | None = None, limit: int = 20
    ) -> list[Task]:
        q: dict[str, Any] = {"user_id": user_id}
        if filters:
            if filters.status:
                q["status"] = filters.status
            if filters.category:
                q["category"] = filters.category
            if filters.due_date_from or filters.due_date_to:
                q["due_date"] = {}
                if filters.due_date_from:
                    q["due_date"]["$gte"] = filters.due_date_from
                if filters.due_date_to:
                    q["due_date"]["$lte"] = filters.due_date_to
        cursor = self.tasks.find(q).limit(limit)
        return [Task.model_validate(d) async for d in cursor]

    async def search_tasks(self, user_id: str, query: str) -> list[Task]:
        cursor = self.tasks.find(
            {"user_id": user_id, "$text": {"$search": query}}
        ).limit(20)
        return [Task.model_validate(d) async for d in cursor]

    # --- Users ---
    async def get_or_create_user(self, user_id: str, **info: Any) -> User:
        doc = await self.users.find_one({"user_id": user_id})
        if doc:
            return User.model_validate(doc)
        user = User(user_id=user_id, **info)
        await self.users.insert_one(user.model_dump(mode="json"))
        return user

    async def get_user(self, user_id: str) -> User | None:
        doc = await self.users.find_one({"user_id": user_id})
        return User.model_validate(doc) if doc else None

    async def update_user_config(self, user_id: str, key: str, value: Any) -> bool:
        r = await self.users.update_one(
            {"user_id": user_id}, {"$set": {key: value, "updated_at": datetime.utcnow()}}
        )
        return r.modified_count > 0

    # --- Conversation context (ReAct pause/resume) ---
    async def get_conversation_context(self, user_id: str) -> dict | None:
        doc = await self.contexts.find_one({"user_id": user_id})
        return doc

    async def save_conversation_context(self, user_id: str, messages: list[dict]) -> bool:
        await self.contexts.update_one(
            {"user_id": user_id},
            {"$set": {"messages": messages, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return True

    async def clear_conversation_context(self, user_id: str) -> bool:
        r = await self.contexts.delete_one({"user_id": user_id})
        return r.deleted_count > 0

    # --- History ---
    async def add_message(
        self, user_id: str, role: str, content: str, **metadata: Any
    ) -> None:
        await self.history.insert_one({
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata,
        })

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict]:
        cursor = (
            self.history.find({"user_id": user_id})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    # --- Jobs ---
    async def create_job(self, job: ScheduledJob) -> str:
        await self.jobs.insert_one(job.model_dump(mode="json"))
        return job.job_id

    async def get_pending_jobs(self, before: datetime) -> list[ScheduledJob]:
        cursor = self.jobs.find({
            "status": "pending",
            "trigger_at": {"$lte": before},
        })
        return [ScheduledJob.model_validate(d) async for d in cursor]

    async def mark_job_fired(self, job_id: str) -> bool:
        r = await self.jobs.update_one(
            {"job_id": job_id}, {"$set": {"status": "fired"}}
        )
        return r.modified_count > 0

    async def mark_job_cancelled(self, job_id: str) -> bool:
        r = await self.jobs.update_one(
            {"job_id": job_id}, {"$set": {"status": "cancelled"}}
        )
        return r.modified_count > 0
