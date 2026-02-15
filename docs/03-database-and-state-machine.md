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

## Collection 3: `conversation_contexts`

Saves the paused ReAct loop state when the LLM calls `ask_user` and waits for a response.
If this document exists for a user, the next message resumes the saved loop.
If it doesn't exist, a fresh ReAct loop starts.

**This replaces the old 10-state FSM.** The LLM manages all "logical states"
(gathering data, confirming deletion, disambiguating, etc.) through the
conversation history stored in `messages`.

```json
{
  "_id": "ObjectId",
  "user_id": "string (Telegram user ID)",
  "messages": "list[dict] — full LLM message array at time of pause",
  "updated_at": "datetime"
}
```

### Indexes
```python
conversation_contexts.create_index("user_id", unique=True)
```

### Lifecycle
- **Created** when LLM calls `ask_user` (loop pauses)
- **Loaded + deleted** when user sends next message (loop resumes)
- **Deleted** on `/start` (reset)

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

## Conversation State (Replacing the Old FSM)

### The Old Problem: 10+ Coded States

The old design had 10+ states (`GATHERING_CREATE`, `CONFIRMING_DELETE`, `DISAMBIGUATING`, etc.)
with hardcoded transition rules enforced by Python code. This was deterministic routing
that should be the LLM's job.

### The New Approach: Conversation Context IS the State

The LLM doesn't need a coded state machine. Its "state" is the **conversation history**.
When the LLM called `ask_user("کی باید بری چشم‌پزشکی؟")` and paused, the conversation
history contains that question. When the user replies "فردا", the LLM sees:

```
[system prompt]
[user] باید برم چشم‌پزشکی
[assistant → tool call: ask_user("کی باید بری چشم‌پزشکی؟")]
[tool result: waiting_for_response]
[user] فردا
```

The LLM knows exactly where it is — it was gathering task creation data. No coded
state machine needed.

### What We Store in MongoDB

Only TWO things:
1. **Conversation history** (the `conversation_history` collection — already defined above)
2. **Saved ReAct context** (for resuming after `ask_user` pauses the loop)

```json
// conversation_contexts collection — saves the paused ReAct loop
{
  "_id": "ObjectId",
  "user_id": "string (Telegram user ID)",
  "messages": "list[dict] — the full LLM message array at time of pause",
  "updated_at": "datetime"
}
```

When the user sends a new message:
- If there's a saved context → **resume** the ReAct loop with the user's reply appended
- If there's no saved context → **start fresh** ReAct loop

When `/start` is sent:
- Delete saved context → next message starts a fresh loop

```python
# The entire "state machine" in code:

async def handle_message(self, user_id: str, message: str) -> str:
    if message.strip() == "/start":
        await self.db.clear_conversation_context(user_id)
        return WELCOME_TEXT

    saved = await self.db.get_conversation_context(user_id)

    if saved:
        # Resume: user is replying to a question from the ReAct loop
        messages = saved["messages"]
        messages.append({"role": "tool", "content": json.dumps({"user_response": message})})
    else:
        # Fresh: new conversation turn
        messages = self._build_fresh_messages(user_id, message)

    return await self._react_loop(user_id, messages)
```

**That's it.** No states, no transitions, no validation rules. The LLM manages all
"logical states" (gathering, confirming, disambiguating) through conversation context.

### Diagram: Old vs New

```
OLD (10 coded states):
  idle → classifying → gathering_create → confirming_create → idle
  idle → classifying → identifying_task → confirming_delete → idle
  ... (10+ states, 20+ transitions, all coded in Python)

NEW (2 infrastructure states):
  no_context → ReAct loop → (LLM returns text) → no_context
  no_context → ReAct loop → (LLM calls ask_user) → has_context
  has_context → Resume ReAct loop → ... → no_context
  /start → clear context → no_context
```

### /start Command — The Universal Reset

At any point, if the user sends `/start`:
1. Saved conversation context is deleted
2. Static welcome message is returned
3. No LLM call needed (must work even if LLM is down)
4. No data is lost (tasks already saved are kept; only in-progress conversation is reset)

### Why This Works

The LLM is better at managing conversational state than coded rules because:
- It handles interruptions naturally ("باید برم دکتر" → [gathering] → "راستی امروز چیکار دارم?" → [handles query, returns to gathering])
- It handles ambiguity ("اونو عوض کن" → it looks at context to understand "اون")
- It handles confirmation in any language/phrasing (not just {"آره", "بله", ...})
- It handles novel situations we didn't code for

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


class SavedReActContext(BaseModel):
    """Saved state of the ReAct loop when paused by ask_user.
    The LLM manages all 'logical states' (gathering, confirming, etc.)
    through the conversation history. No coded FSM states."""
    user_id: str
    messages: list[dict]  # Full LLM message array at time of pause
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
    MAX_TOOL_CALLS_PER_MESSAGE: int = 10
    RATE_LIMIT_PER_MINUTE: int = 10

    class Config:
        env_file = ".env"
```
