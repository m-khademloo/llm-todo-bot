# 03 - Database Schema & State Machine

## MongoDB Database Design

Database name: `llm_todo_bot`

We use **5 collections**, each documented below with full schemas.

---

## Collection 1: `tasks`

The core collection. Each document is a single task belonging to a single user.

```json
{
  "_id": "ObjectId",
  "task_id": "uuid4 string (user-facing ID, shorter for display)",
  "user_id": "string (Telegram user ID)",
  "title": "string",
  "description": "string | null",
  "due_date": "datetime | null",
  "priority": "int (1-5, 1=highest)",
  "category": "string (health | work | family | learning | personal | other)",
  "status": "string (pending | done | cancelled)",
  "estimated_time_minutes": "int | null",
  "tags": ["string"],
  "reminder": {
    "enabled": "bool",
    "remind_at": "datetime | null",
    "reminded": "bool (has the reminder been sent?)"
  },
  "recurrence": {
    "enabled": "bool",
    "pattern": "string | null (daily | weekly | monthly | custom_cron)",
    "next_occurrence": "datetime | null",
    "end_date": "datetime | null"
  },
  "created_at": "datetime",
  "updated_at": "datetime",
  "completed_at": "datetime | null"
}
```

### Indexes
```python
# Essential indexes
tasks.create_index([("user_id", 1), ("status", 1)])              # Most common query
tasks.create_index([("user_id", 1), ("due_date", 1)])             # Date-based queries
tasks.create_index([("user_id", 1), ("category", 1)])             # Category filter
tasks.create_index([("reminder.remind_at", 1)], sparse=True)      # Reminder scheduler
tasks.create_index([("recurrence.next_occurrence", 1)], sparse=True)  # Recurring scheduler
tasks.create_index([("user_id", 1), ("title", "text")])           # Text search
```

---

## Collection 2: `users`

User profile and configuration.

```json
{
  "_id": "ObjectId",
  "user_id": "string (Telegram user ID)",
  "telegram_username": "string | null",
  "first_name": "string",
  "last_name": "string | null",
  "language": "string (fa | en, default: fa)",
  "timezone": "string (default: Asia/Tehran)",
  "priority_prompt": "string | null (user's custom priority instructions)",
  "default_category": "string (default: personal)",
  "notification_enabled": "bool (default: true)",
  "quiet_hours": {
    "enabled": "bool",
    "start": "string (HH:MM, e.g., '23:00')",
    "end": "string (HH:MM, e.g., '07:00')"
  },
  "created_at": "datetime",
  "updated_at": "datetime",
  "message_count": "int (total messages sent)",
  "task_count": "int (total tasks created)"
}
```

### Indexes
```python
users.create_index("user_id", unique=True)
```

### Priority Prompt Examples

When user says: "اولویت منو اینجوری تنظیم کن: ۱. سلامت ۲. کار ۳. خانواده ۴. یادگیری"

We store:
```json
{
  "priority_prompt": "User's priority ordering: 1. Health (سلامت) 2. Work (کار) 3. Family (خانواده) 4. Learning (یادگیری). Health-related tasks should generally be priority 1-2. Work tasks 2-3. Family 3-4. Learning 4-5. Adjust based on urgency."
}
```

This string is injected into the Priority Agent's system prompt.

---

## Collection 3: `conversation_states`

The FSM state for each user, persisted so it survives bot restarts.

```json
{
  "_id": "ObjectId",
  "user_id": "string (Telegram user ID)",
  "fsm_state": "string (see FSM states below)",
  "context": {
    "intent": "string | null (current intent being processed)",
    "partial_task": "dict | null (task being gathered)",
    "task_reference": "string | null (task_id being updated/deleted/completed)",
    "matched_tasks": "list | null (multiple matches for disambiguation)",
    "gather_turn_count": "int (how many gather questions asked)",
    "confirmation_data": "dict | null (what we're asking to confirm)",
    "pending_action": "string | null (action waiting for confirmation)"
  },
  "updated_at": "datetime"
}
```

### Indexes
```python
conversation_states.create_index("user_id", unique=True)
```

---

## Collection 4: `conversation_history`

Stores message history for context.

```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "role": "string (user | assistant | system)",
  "content": "string",
  "timestamp": "datetime",
  "metadata": {
    "intent": "string | null",
    "model_used": "string | null",
    "tokens_used": "int | null",
    "processing_time_ms": "int | null"
  }
}
```

### Indexes
```python
conversation_history.create_index([("user_id", 1), ("timestamp", -1)])
# TTL index: auto-delete messages older than 30 days
conversation_history.create_index("timestamp", expireAfterSeconds=2592000)
```

---

## Collection 5: `scheduled_jobs`

Persistent storage for scheduled reminders and recurring task triggers. Works with APScheduler's MongoDB job store, but we also store our own metadata.

```json
{
  "_id": "ObjectId",
  "job_id": "string (APScheduler job ID)",
  "user_id": "string",
  "job_type": "string (reminder | recurring_task | due_date_alert)",
  "task_id": "string | null (linked task)",
  "trigger_at": "datetime",
  "message": "string (what to send)",
  "recurrence_pattern": "string | null",
  "status": "string (pending | fired | cancelled)",
  "created_at": "datetime"
}
```

### Indexes
```python
scheduled_jobs.create_index([("trigger_at", 1), ("status", 1)])
scheduled_jobs.create_index("user_id")
scheduled_jobs.create_index("task_id", sparse=True)
```

---

## Finite State Machine (FSM)

### States

```
┌─────────┐
│  IDLE   │ ◄─── Default state. Waiting for user input.
└────┬────┘
     │ (user sends message)
     │
     ▼
┌─────────────────┐
│   CLASSIFYING   │  Transient state (no user waiting here).
└────┬────────────┘  Classifier runs and immediately transitions.
     │
     ├── intent = create_task ──────► GATHERING_CREATE
     ├── intent = update_task ──────► IDENTIFYING_TASK (then GATHERING_UPDATE)
     ├── intent = delete_task ──────► IDENTIFYING_TASK (then CONFIRMING_DELETE)
     ├── intent = complete_task ────► IDENTIFYING_TASK (then CONFIRMING_COMPLETE)
     ├── intent = query_tasks ──────► (execute immediately, return to IDLE)
     ├── intent = set_config ───────► CONFIRMING_CONFIG
     ├── intent = smalltalk ────────► (respond immediately, return to IDLE)
     └── intent = unclear ──────────► (ask clarification, return to IDLE)
```

### Detailed State Diagram

```
                          /start
                            │
                            ▼
                     ┌──────────┐
          ┌─────────│   IDLE   │◄──────────────────────────────┐
          │         └──────────┘                                │
          │              │                                      │
          │         (message)                                   │
          │              │                                      │
          │              ▼                                      │
          │      ┌───────────────┐                             │
          │      │  CLASSIFYING  │                             │
          │      └───────┬───────┘                             │
          │              │                                      │
          │    ┌─────────┼─────────┬──────────┐               │
          │    ▼         ▼         ▼          ▼               │
          │ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐    │
          │ │GATHER  │ │IDENTIFY│ │CONFIRM │ │ EXECUTE  │    │
          │ │CREATE  │ │TASK    │ │CONFIG  │ │ & REPLY  │────┘
          │ └───┬────┘ └───┬────┘ └───┬────┘ └──────────┘
          │     │          │          │
          │     ▼          ▼          │     ┌──────────┐
          │ ┌────────┐ ┌────────┐    ├────►│  DONE    │───┐
          │ │CONFIRM │ │GATHER  │    │     └──────────┘   │
          │ │CREATE  │ │UPDATE  │    │                    │
          │ └───┬────┘ └───┬────┘    │                    │
          │     │          │         │                    │
          │     ▼          ▼         ▼                    │
          │ ┌────────┐ ┌────────┐ ┌────────┐             │
          │ │EXECUTE │ │CONFIRM │ │CONFIRM │             │
          │ │CREATE  │ │UPDATE  │ │DELETE  │             │
          │ └───┬────┘ └───┬────┘ └───┬────┘             │
          │     │          │          │                   │
          │     └──────────┴──────────┘                   │
          │                │                              │
          │                ▼                              │
          │         ┌──────────┐                          │
          │         │   IDLE   │◄─────────────────────────┘
          │         └──────────┘
          │
          │  (at ANY point, user sends /start)
          └──────────────────────────────────────► IDLE (reset)
```

### State Definitions

| State | Description | Valid Transitions |
|-------|-------------|-------------------|
| `idle` | Waiting for user input. No active conversation. | → classifying |
| `gathering_create` | Collecting data for new task. Multi-turn. | → confirming_create, → idle (/start) |
| `gathering_update` | Collecting update data. | → confirming_update, → idle (/start) |
| `identifying_task` | Need to figure out which task user means. | → gathering_update, → confirming_delete, → confirming_complete, → idle (/start) |
| `confirming_create` | Showing task summary, waiting for yes/no. | → idle (execute or cancel) |
| `confirming_update` | Showing update summary, waiting for yes/no. | → idle (execute or cancel) |
| `confirming_delete` | Asking if user really wants to delete. | → idle (execute or cancel) |
| `confirming_complete` | Asking if user wants to mark as done. | → idle (execute or cancel) |
| `confirming_config` | Asking if config change is correct. | → idle (execute or cancel) |
| `disambiguating` | Multiple tasks match, asking user to pick one. | → confirming_*, → idle (/start) |

### State Transition Rules

```python
VALID_TRANSITIONS = {
    "idle":                ["gathering_create", "gathering_update", "identifying_task",
                            "confirming_config", "confirming_complete", "disambiguating", "idle"],
    "gathering_create":    ["confirming_create", "gathering_create", "idle"],
    "gathering_update":    ["confirming_update", "gathering_update", "idle"],
    "identifying_task":    ["gathering_update", "confirming_delete", "confirming_complete",
                            "disambiguating", "idle"],
    "confirming_create":   ["idle"],
    "confirming_update":   ["idle"],
    "confirming_delete":   ["idle"],
    "confirming_complete": ["idle"],
    "confirming_config":   ["idle"],
    "disambiguating":      ["confirming_delete", "confirming_complete", "confirming_update",
                            "gathering_update", "idle"],
}
```

### /start Command — The Universal Reset

At any state, if the user sends `/start`:
1. Current state context is cleared
2. State is set to `idle`
3. Bot responds with welcome message
4. No data is lost (tasks already saved are kept; only in-progress conversation is reset)

```python
async def handle_start(user_id: str, state: ConversationState):
    state.fsm_state = "idle"
    state.context = {}  # Clear all context
    await db.save_state(state)
    return "سلام! 👋 من دستیار مدیریت تسک‌هات هستم. بگو چیکار کنم!"
```

---

## Task Identification (The "Which Task?" Problem)

When a user says "چشمم خوب شد" (my eye is better), we need to find the matching task. This is handled by the **task identification** flow:

### Strategy

```python
async def identify_task(user_id: str, message: str, intent: str) -> IdentificationResult:
    """Find which task the user is referring to."""

    # 1. Get all pending tasks for user
    tasks = await db.get_tasks(user_id, status="pending")

    if not tasks:
        return IdentificationResult(found=False, message="تسک فعالی نداری!")

    # 2. Use LLM to match message to tasks
    match_result = await llm.call(
        system_prompt=TASK_MATCHER_PROMPT,
        user_message=json.dumps({
            "user_message": message,
            "tasks": [t.summary() for t in tasks]
        })
    )

    # 3. Evaluate matches
    matches = match_result["matches"]  # List of {task_id, confidence}

    if len(matches) == 0:
        return IdentificationResult(found=False, message="هیچ تسکی پیدا نکردم که مربوط باشه. کدوم تسکو میگی؟")

    if len(matches) == 1 and matches[0]["confidence"] > 0.8:
        return IdentificationResult(found=True, task_id=matches[0]["task_id"])

    # Multiple matches or low confidence → ask user
    return IdentificationResult(
        found=False,
        ambiguous=True,
        candidates=matches,
        message=format_disambiguation(matches)  # "کدوم یکی از اینا رو میگی؟\n1. ...\n2. ..."
    )
```

---

## Database Access Layer

All database operations go through a single `Database` class. No raw MongoDB calls outside this class.

```python
class Database:
    """Async MongoDB access layer."""

    def __init__(self, mongo_uri: str, db_name: str = "llm_todo_bot"):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.tasks = self.db["tasks"]
        self.users = self.db["users"]
        self.states = self.db["conversation_states"]
        self.history = self.db["conversation_history"]
        self.jobs = self.db["scheduled_jobs"]

    async def setup_indexes(self):
        """Create all indexes. Call once on startup."""
        # ... all indexes defined above ...

    # --- Tasks ---
    async def create_task(self, task: Task) -> str: ...
    async def get_task(self, user_id: str, task_id: str) -> Task | None: ...
    async def update_task(self, user_id: str, task_id: str, updates: dict) -> bool: ...
    async def delete_task(self, user_id: str, task_id: str) -> bool: ...
    async def complete_task(self, user_id: str, task_id: str) -> bool: ...
    async def query_tasks(self, user_id: str, filters: TaskFilter) -> list[Task]: ...
    async def search_tasks(self, user_id: str, query: str) -> list[Task]: ...

    # --- Users ---
    async def get_or_create_user(self, user_id: str, **info) -> User: ...
    async def update_user_config(self, user_id: str, key: str, value: Any) -> bool: ...

    # --- State ---
    async def get_state(self, user_id: str) -> ConversationState: ...
    async def save_state(self, state: ConversationState) -> bool: ...
    async def reset_state(self, user_id: str) -> bool: ...

    # --- History ---
    async def add_message(self, user_id: str, role: str, content: str, **metadata) -> None: ...
    async def get_history(self, user_id: str, limit: int = 10) -> list[Message]: ...

    # --- Jobs ---
    async def create_job(self, job: ScheduledJob) -> str: ...
    async def get_pending_jobs(self, before: datetime) -> list[ScheduledJob]: ...
    async def mark_job_fired(self, job_id: str) -> bool: ...
```

### User Isolation
Every method that touches user data takes `user_id` as the first parameter and includes it in every query filter. There is no way to accidentally query another user's data.

```python
# EVERY query includes user_id
async def query_tasks(self, user_id: str, filters: TaskFilter) -> list[Task]:
    query = {"user_id": user_id}  # Always starts with user isolation
    if filters.status:
        query["status"] = filters.status
    # ...
    return await self.tasks.find(query).to_list()
```

---

## Data Models (Pydantic)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


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
    pattern: str | None = None  # daily, weekly, monthly, cron expression
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
    reminder: ReminderConfig = ReminderConfig()
    recurrence: RecurrenceConfig = RecurrenceConfig()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class FSMState(str, Enum):
    IDLE = "idle"
    GATHERING_CREATE = "gathering_create"
    GATHERING_UPDATE = "gathering_update"
    IDENTIFYING_TASK = "identifying_task"
    CONFIRMING_CREATE = "confirming_create"
    CONFIRMING_UPDATE = "confirming_update"
    CONFIRMING_DELETE = "confirming_delete"
    CONFIRMING_COMPLETE = "confirming_complete"
    CONFIRMING_CONFIG = "confirming_config"
    DISAMBIGUATING = "disambiguating"


class ConversationContext(BaseModel):
    intent: str | None = None
    partial_task: dict | None = None
    task_reference: str | None = None
    matched_tasks: list[dict] | None = None
    gather_turn_count: int = 0
    confirmation_data: dict | None = None
    pending_action: str | None = None


class ConversationState(BaseModel):
    user_id: str
    fsm_state: FSMState = FSMState.IDLE
    context: ConversationContext = ConversationContext()
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## MongoDB Connection & Configuration

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "llm_todo_bot"

    # LLM
    LLM_MODEL: str = "ollama/deepseek-r1:14b"
    LLM_BASE_URL: str | None = "http://localhost:11434"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1000

    # Scheduler
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60

    # Limits
    MAX_TASKS_PER_USER: int = 200
    MAX_GATHER_TURNS: int = 3
    RATE_LIMIT_PER_MINUTE: int = 10

    class Config:
        env_file = ".env"
```
