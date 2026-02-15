"""Pydantic models for tasks, users, and state."""
from datetime import datetime
from enum import Enum
from typing import Any

import uuid
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskCategory(str, Enum):
    HEALTH = "health"
    WORK = "work"
    FAMILY = "family"
    LEARNING = "learning"
    PERSONAL = "personal"
    OTHER = "other"


class ReminderConfig(BaseModel):
    enabled: bool = False
    remind_at: datetime | None = None
    reminded: bool = False


class RecurrenceConfig(BaseModel):
    enabled: bool = False
    pattern: str | None = None
    next_occurrence: datetime | None = None
    end_date: datetime | None = None


class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str
    title: str
    description: str | None = None
    due_date: datetime | None = None
    priority: int = Field(default=3, ge=1, le=5)
    category: TaskCategory = TaskCategory.PERSONAL
    status: TaskStatus = TaskStatus.PENDING
    estimated_time_minutes: int | None = None
    tags: list[str] = []
    reminder: ReminderConfig = Field(default_factory=ReminderConfig)
    recurrence: RecurrenceConfig = Field(default_factory=RecurrenceConfig)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class QuietHoursConfig(BaseModel):
    enabled: bool = False
    start: str = "23:00"
    end: str = "07:00"


class User(BaseModel):
    user_id: str
    telegram_username: str | None = None
    first_name: str = ""
    last_name: str | None = None
    language: str = "fa"
    timezone: str = "Asia/Tehran"
    priority_prompt: str | None = None
    default_category: str = "personal"
    notification_enabled: bool = True
    quiet_hours: QuietHoursConfig = Field(default_factory=QuietHoursConfig)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    task_count: int = 0


class SavedReActContext(BaseModel):
    user_id: str
    messages: list[dict]
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskFilter(BaseModel):
    status: str | None = None
    category: str | None = None
    due_date_from: datetime | None = None
    due_date_to: datetime | None = None


class ScheduledJob(BaseModel):
    job_id: str
    user_id: str
    job_type: str  # reminder | recurring_task | due_date_alert
    task_id: str | None = None
    trigger_at: datetime
    message: str
    recurrence_pattern: str | None = None
    status: str = "pending"  # pending | fired | cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)
