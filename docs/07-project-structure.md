# 07 - Project Structure & Implementation Guide

## Directory Layout

```
llm-todo-bot/
│
├── docs/                          # Design documents (you are here)
│   ├── 01-architecture-overview.md
│   ├── 02-agentic-design.md       # THE MOST IMPORTANT DOC — ReAct loop, tools, orchestrator
│   ├── 03-database-and-state-machine.md
│   ├── 04-task-lifecycle.md
│   ├── 05-scheduling-and-reminders.md
│   ├── 06-user-experience.md
│   └── 07-project-structure.md
│
├── src/                           # Application source code
│   ├── __init__.py
│   ├── main.py                    # Entry point: start bot + scheduler
│   ├── config.py                  # Pydantic settings from .env
│   │
│   ├── bot/                       # Telegram bot layer (thin — just receives/sends)
│   │   ├── __init__.py
│   │   ├── handlers.py            # Telegram message/command handlers → calls orchestrator
│   │   └── middleware.py          # Rate limiting, user onboarding
│   │
│   ├── orchestrator/              # The Brain — ReAct loop + tool calling
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Main ReAct loop: Planner → Executor → Observer
│   │   ├── tool_executor.py       # Executes tool calls safely (the Python side)
│   │   ├── tool_registry.py       # All tool definitions (names, params, descriptions)
│   │   ├── safety.py              # Confirmation logic, user isolation, rate limits
│   │   └── state_manager.py       # FSM state persistence + ReAct loop state save/resume
│   │
│   ├── tools/                     # Individual tool implementations
│   │   ├── __init__.py
│   │   ├── datetime_tools.py      # get_current_datetime
│   │   ├── task_tools.py          # get_user_tasks, create_task, update_task, complete_task, request_task_deletion
│   │   ├── config_tools.py        # get_user_config, update_user_config
│   │   ├── scheduling_tools.py    # set_reminder, recurring task management
│   │   ├── conversation_tools.py  # ask_user (pause/resume ReAct loop)
│   │   └── priority_tools.py      # calculate_priority (sub-agent: uses LLM internally)
│   │
│   ├── db/                        # Database layer
│   │   ├── __init__.py
│   │   ├── database.py            # MongoDB connection & access layer
│   │   └── models.py              # Pydantic models (Task, User, State, etc.)
│   │
│   ├── llm/                       # LLM client layer
│   │   ├── __init__.py
│   │   ├── client.py              # LiteLLM wrapper: call_with_tools + call_simple
│   │   └── fallback.py            # Prompt-based tool calling for models without native support
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── persian.py             # Persian number/text utilities
│       ├── i18n.py                # Template strings & language detection
│       └── logging.py             # Structured logging setup
│
├── prompts/                       # LLM prompt templates (text files)
│   ├── system_base.txt            # Base system prompt (static parts)
│   ├── priority_calculator.txt    # Sub-agent prompt for priority calculation
│   ├── tool_descriptions.txt      # Tool docs for prompt-based fallback (non-native tool calling)
│   └── fallback_responses.txt     # Canned responses for error cases
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures (MockLLM, MockDB, etc.)
│   ├── test_tools/                # Unit tests for each tool
│   │   ├── test_datetime_tools.py
│   │   ├── test_task_tools.py
│   │   ├── test_config_tools.py
│   │   └── test_scheduling_tools.py
│   ├── test_orchestrator.py       # ReAct loop integration tests
│   ├── test_state_manager.py      # State save/resume tests
│   ├── test_safety.py             # Confirmation, user isolation tests
│   └── fixtures/                  # Test conversation fixtures
│       ├── create_task_flow.yaml
│       ├── query_tasks_flow.yaml
│       └── delete_with_confirmation.yaml
│
├── .env.example                   # Example environment variables
├── .gitignore
├── pyproject.toml                 # Project metadata & dependencies
├── requirements.txt               # Pinned dependencies
├── Dockerfile                     # Container build (non-root, read-only)
├── docker-compose.yml             # Bot + MongoDB + Ollama (optional)
└── README.md                      # Setup & run instructions
```

---

## Module Dependency Graph

```
                    main.py
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
           bot/    core/    scheduler
              │        │        │
              ▼        ▼        ▼
           agents/ ◄───┘    db/
              │              │
              ▼              ▼
           llm/          MongoDB
```

**Key rules:**
- `bot/` depends on `agents/` and `core/` — never the other way around
- `agents/` depends on `llm/` and `db/` — never on `bot/`
- `core/` depends on `db/` — never on `agents/` or `bot/`
- `db/` depends on nothing (only `motor` and `pydantic`)
- `llm/` depends on nothing (only `litellm`)
- `utils/` depends on nothing (pure utility functions)

This means you can test agents without Telegram, test core logic without LLM, and test DB layer without anything else.

---

## Implementation Order

Build in this exact order. Each phase is independently testable.

### Phase 1: Foundation (Day 1)
**Goal:** Bot runs, connects to MongoDB, responds to `/start`

| # | Task | File(s) |
|---|------|---------|
| 1.1 | Set up project, install dependencies | `pyproject.toml`, `requirements.txt` |
| 1.2 | Create config module | `src/config.py` |
| 1.3 | Create data models | `src/db/models.py` |
| 1.4 | Create database layer | `src/db/database.py` |
| 1.5 | Create basic bot with `/start` handler | `src/bot/handlers.py`, `src/main.py` |
| 1.6 | Test: bot responds to `/start`, user saved in DB | Manual test |

**Dependencies to install:**
```
python-telegram-bot>=21.0
litellm>=1.30.0
motor>=3.3.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
apscheduler>=3.10.0
pymongo>=4.6.0
structlog>=24.1.0
jdatetime>=5.0.0
croniter>=2.0.0
pytz>=2024.1
```

### Phase 2: LLM Integration (Day 2)
**Goal:** Bot classifies messages and responds

| # | Task | File(s) |
|---|------|---------|
| 2.1 | Create LLM client wrapper | `src/llm/client.py` |
| 2.2 | Write classifier prompt | `prompts/classifier.txt` |
| 2.3 | Implement classifier agent | `src/agents/classifier.py` |
| 2.4 | Create orchestrator skeleton | `src/agents/orchestrator.py` |
| 2.5 | Wire bot → orchestrator → classifier | `src/bot/handlers.py` |
| 2.6 | Test: send messages, see classification logs | Manual test |

### Phase 3: Task Creation (Day 3)
**Goal:** Full create-task flow works

| # | Task | File(s) |
|---|------|---------|
| 3.1 | Implement state machine | `src/core/state_machine.py` |
| 3.2 | Write data gatherer prompt | `prompts/data_gatherer.txt` |
| 3.3 | Implement data gatherer agent | `src/agents/data_gatherer.py` |
| 3.4 | Implement date resolver | `src/core/date_resolver.py` |
| 3.5 | Implement task service (create) | `src/core/task_service.py` |
| 3.6 | Write priority prompt | `prompts/priority_calculator.txt` |
| 3.7 | Implement priority agent | `src/agents/priority.py` |
| 3.8 | Implement response formatter | `src/agents/response_formatter.py` |
| 3.9 | Wire full create flow in orchestrator | `src/agents/orchestrator.py` |
| 3.10 | Test: create task via conversation | Manual test |

### Phase 4: Task Queries (Day 4)
**Goal:** User can query tasks

| # | Task | File(s) |
|---|------|---------|
| 4.1 | Implement query builder | `src/core/task_service.py` |
| 4.2 | Implement task list formatting | `src/bot/formatters.py` |
| 4.3 | Persian date display | `src/utils/persian.py` |
| 4.4 | Wire query flow in orchestrator | `src/agents/orchestrator.py` |
| 4.5 | Test: "امروز چیکار دارم؟" works | Manual test |

### Phase 5: Update, Complete, Delete (Day 5)
**Goal:** Full CRUD working

| # | Task | File(s) |
|---|------|---------|
| 5.1 | Implement task matcher agent | `src/agents/task_matcher.py` |
| 5.2 | Implement disambiguation flow | `src/agents/orchestrator.py` |
| 5.3 | Implement update flow | `src/core/task_service.py` |
| 5.4 | Implement complete flow | `src/core/task_service.py` |
| 5.5 | Implement delete flow (with confirmation) | `src/core/task_service.py` |
| 5.6 | Wire all in orchestrator | `src/agents/orchestrator.py` |
| 5.7 | Test: update, complete, delete tasks | Manual test |

### Phase 6: Scheduling & Reminders (Day 6)
**Goal:** Reminders and recurring tasks work

| # | Task | File(s) |
|---|------|---------|
| 6.1 | Set up APScheduler with MongoDB store | `src/core/scheduler_service.py` |
| 6.2 | Implement reminder creation | `src/core/scheduler_service.py` |
| 6.3 | Implement reminder firing | `src/core/scheduler_service.py` |
| 6.4 | Implement due-date alerts | `src/core/scheduler_service.py` |
| 6.5 | Implement recurring tasks | `src/core/scheduler_service.py` |
| 6.6 | Test: set reminder, wait, receive notification | Manual test |

### Phase 7: Polish (Day 7)
**Goal:** Production-ready

| # | Task | File(s) |
|---|------|---------|
| 7.1 | User config (priority prompt, quiet hours) | `src/core/user_service.py` |
| 7.2 | Rate limiting | `src/bot/middleware.py` |
| 7.3 | Error handling & recovery | Throughout |
| 7.4 | Logging | `src/utils/logging.py` |
| 7.5 | Smalltalk handling | `src/agents/orchestrator.py` |
| 7.6 | Docker setup | `Dockerfile`, `docker-compose.yml` |
| 7.7 | Write tests | `tests/` |
| 7.8 | README | `README.md` |

---

## Key Implementation Details

### main.py — Entry Point

```python
import asyncio
from src.config import settings
from src.db.database import Database
from src.llm.client import LLMClient
from src.bot.handlers import create_bot
from src.core.scheduler_service import SchedulerService

async def main():
    # 1. Connect to MongoDB
    db = Database(settings.MONGO_URI, settings.MONGO_DB_NAME)
    await db.setup_indexes()

    # 2. Create LLM client
    llm = LLMClient(model=settings.LLM_MODEL, base_url=settings.LLM_BASE_URL)

    # 3. Create scheduler
    scheduler = SchedulerService(settings.MONGO_URI, settings.MONGO_DB_NAME)

    # 4. Create and start bot
    bot = create_bot(settings.TELEGRAM_BOT_TOKEN, db, llm, scheduler)

    # 5. Start scheduler
    await scheduler.start(bot)

    # 6. Run bot (polling mode for development)
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
```

### Dependency Injection Pattern

No DI framework. Simple constructor injection:

```python
# The orchestrator receives its dependencies via __init__
class Orchestrator:
    def __init__(self, db: Database, llm: LLMClient, scheduler: SchedulerService):
        self.db = db
        self.llm = llm
        self.scheduler = scheduler
        self.classifier = ClassifierAgent(llm)
        self.resolver = ResolverAgent(llm)     # Resolves user message against real DB data
        self.gatherer = DataGathererAgent(llm)
        self.priority = PriorityAgent(llm)
        self.formatter = ResponseFormatterAgent(llm)
        self.task_service = TaskService(db)
        self.user_service = UserService(db)
        self.state_machine = StateMachine(db)
```

### Agent Base Class

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Base class for all LLM agents."""

    def __init__(self, llm: LLMClient, prompt_name: str):
        self.llm = llm
        self.prompt_name = prompt_name
        self._prompt_template: str | None = None

    async def get_prompt(self, **kwargs) -> str:
        """Load and fill prompt template."""
        if self._prompt_template is None:
            self._prompt_template = await load_prompt(self.prompt_name)
        return self._prompt_template.format(**kwargs)

    @abstractmethod
    async def run(self, **kwargs) -> dict:
        """Execute the agent. Returns structured dict."""
        ...

    async def _call_llm_json(self, system_prompt: str, user_message: str) -> dict:
        """Call LLM and parse JSON response with retry logic."""
        return await safe_llm_json_call(self.llm, system_prompt, user_message)
```

### Adding a New Agent (Contributor Guide)

To add a new agent (e.g., a "task suggestion" agent):

1. **Create prompt file:** `prompts/task_suggester.txt`
2. **Create agent class:** `src/agents/task_suggester.py`
   ```python
   from src.agents.base import BaseAgent

   class TaskSuggesterAgent(BaseAgent):
       def __init__(self, llm):
           super().__init__(llm, "task_suggester")

       async def run(self, user_id: str, current_tasks: list) -> dict:
           prompt = await self.get_prompt(tasks=json.dumps(current_tasks))
           return await self._call_llm_json(prompt, "Suggest tasks")
   ```
3. **Register in orchestrator:** Add to `Orchestrator.__init__` and add routing logic
4. **Add intent to classifier:** Update `prompts/classifier.txt` with new intent
5. **Write tests:** `tests/test_task_suggester.py`

---

## Environment Configuration

### .env.example

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=llm_todo_bot

# LLM Provider (pick one)
# --- Ollama (local) ---
LLM_MODEL=ollama/deepseek-r1:14b
LLM_BASE_URL=http://localhost:11434

# --- OpenAI ---
# LLM_MODEL=gpt-4o-mini
# OPENAI_API_KEY=sk-...

# --- DeepSeek ---
# LLM_MODEL=deepseek/deepseek-chat
# DEEPSEEK_API_KEY=sk-...

# --- Anthropic ---
# LLM_MODEL=anthropic/claude-3-haiku-20240307
# ANTHROPIC_API_KEY=sk-ant-...

# Settings
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000
MAX_TASKS_PER_USER=200
MAX_GATHER_TURNS=3
RATE_LIMIT_PER_MINUTE=10
REMINDER_CHECK_INTERVAL_SECONDS=60
```

### Docker Compose

```yaml
version: "3.8"

services:
  bot:
    build: .
    env_file: .env
    depends_on:
      - mongo
    restart: unless-stopped
    volumes:
      - ./prompts:/app/prompts  # Hot-reload prompts without rebuild

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY prompts/ prompts/

CMD ["python", "-m", "src.main"]
```

---

## Testing Strategy

### Unit Tests (No External Dependencies)

```python
# tests/test_state_machine.py
import pytest
from src.core.state_machine import StateMachine, FSMState

def test_valid_transition():
    sm = StateMachine()
    assert sm.can_transition("idle", "gathering_create") is True

def test_invalid_transition():
    sm = StateMachine()
    assert sm.can_transition("idle", "confirming_delete") is False

def test_start_resets_to_idle():
    sm = StateMachine()
    assert sm.handle_start("gathering_create") == "idle"
```

```python
# tests/test_date_resolver.py
import pytest
from datetime import datetime, timedelta
from src.core.date_resolver import DateResolver

def test_resolve_farda():
    resolver = DateResolver()
    result = resolver.resolve("فردا")
    expected = datetime.now() + timedelta(days=1)
    assert result.date() == expected.date()

def test_resolve_three_days():
    resolver = DateResolver()
    result = resolver.resolve("سه روز دیگه")
    expected = datetime.now() + timedelta(days=3)
    assert result.date() == expected.date()
```

### Integration Tests (With Mock LLM)

```python
# tests/test_orchestrator.py
import pytest
from unittest.mock import AsyncMock
from src.agents.orchestrator import Orchestrator

@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.call.return_value = json.dumps({
        "intent": "create_task",
        "confidence": 0.95,
        "extracted_entities": {"title": "دکتر", "category": "health"}
    })
    return llm

@pytest.mark.asyncio
async def test_create_task_flow(mock_llm, mock_db):
    orch = Orchestrator(db=mock_db, llm=mock_llm, scheduler=AsyncMock())
    response = await orch.handle_message("user123", "باید برم دکتر")
    assert "دکتر" in response
```

### End-to-End Tests (With Real LLM)

For E2E tests, use a cheap model and record the conversations:

```python
# tests/e2e/test_full_flow.py
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_task_lifecycle():
    """Test: create → query → complete → query (should be empty)."""
    bot = create_test_bot()  # Uses real LLM, test MongoDB

    # Create
    response = await bot.handle("فردا جلسه دارم")
    assert "جلسه" in response

    # Query
    response = await bot.handle("تسک‌هام چیه؟")
    assert "جلسه" in response

    # Complete
    response = await bot.handle("جلسه تموم شد")
    assert "تکمیل" in response or "✅" in response

    # Query again
    response = await bot.handle("تسک‌های فعال")
    assert "جلسه" not in response
```

---

## Monitoring & Observability

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Every log entry includes context
logger.info("message_received",
    user_id="12345",
    message_length=42,
    fsm_state="idle",
)

logger.info("llm_call",
    agent="classifier",
    model="deepseek-chat",
    tokens_used=150,
    latency_ms=320,
)

logger.info("task_created",
    user_id="12345",
    task_id="abc123",
    category="health",
    priority=1,
)
```

### Key Metrics to Log

| Event | Fields |
|-------|--------|
| Message received | `user_id`, `message_length`, `fsm_state` |
| LLM call | `agent`, `model`, `tokens_used`, `latency_ms`, `success` |
| Intent classified | `user_id`, `intent`, `confidence` |
| Task CRUD | `user_id`, `task_id`, `operation`, `category` |
| Reminder fired | `user_id`, `task_id`, `delay_from_scheduled_ms` |
| Error | `user_id`, `error_type`, `error_message`, `stack_trace` |

### Health Check

A simple way to verify the bot is running:

```python
# In main.py, log a heartbeat every 5 minutes
scheduler.add_job(
    lambda: logger.info("heartbeat", active_users=len(active_sessions)),
    trigger="interval",
    minutes=5,
    id="heartbeat",
)
```

---

## Security Checklist

- [ ] Bot token in `.env`, not in code
- [ ] `.env` in `.gitignore`
- [ ] All DB queries include `user_id` filter
- [ ] Destructive actions require confirmation
- [ ] System prompts not exposed to users
- [ ] User input sanitized before DB queries (Pydantic handles this)
- [ ] Rate limiting active
- [ ] No `eval()` or `exec()` of user input
- [ ] Prompt injection: user messages wrapped in clear delimiters
- [ ] MongoDB auth enabled in production (not default `localhost` without auth)

---

## Migration / Upgrade Path

### Schema Changes
Since MongoDB is schemaless, adding new fields is easy:
1. Add field to Pydantic model with a default value
2. New documents get the field automatically
3. Old documents get the default when loaded by Pydantic

### Changing LLM Provider
Just update `.env`:
```bash
# Was:
LLM_MODEL=ollama/deepseek-r1:14b
# Now:
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

No code changes needed. LiteLLM handles the provider switch.

### Adding New Intents
1. Update `prompts/classifier.txt` with the new intent
2. Create handler in orchestrator
3. Create any new agents needed
4. The FSM may need new states (add to `state_machine.py`)

---

## Summary: What Makes This Design Good for Contribution

1. **Clear boundaries** — Each module has one job. Agents don't know about Telegram. The bot doesn't know about MongoDB queries.
2. **Prompts are data, not code** — Change LLM behavior by editing `.txt` files, no Python changes needed.
3. **Agents are pluggable** — New agent = new file + register in orchestrator.
4. **State machine is explicit** — All states and transitions are documented and validated.
5. **Tests don't need infrastructure** — Mock the LLM, mock the DB, test the logic.
6. **Single entry point** — `python -m src.main` runs everything.
7. **Docker for easy setup** — `docker-compose up` and you're running.
