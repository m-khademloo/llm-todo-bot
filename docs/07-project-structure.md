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
              ┌────────┼──────────┐
              ▼        ▼          ▼
           bot/    orchestrator/  scheduler (APScheduler)
              │        │
              │        ├── tools/      (tool implementations)
              │        ├── llm/        (LLM client)
              │        └── db/         (database layer)
              │
              └──► orchestrator/       (bot calls orchestrator.handle_message)
```

**Key rules:**
- `bot/` depends on `orchestrator/` only — calls `orchestrator.handle_message(user_id, text)`
- `orchestrator/` depends on `tools/`, `llm/`, `db/` — it's the central coordinator
- `tools/` depends on `db/` and `llm/` (some tools like `calculate_priority` are sub-agents)
- `db/` depends on nothing (only `motor` and `pydantic`)
- `llm/` depends on nothing (only `litellm`)
- `utils/` depends on nothing (pure utility functions)

**Adding a new tool requires touching:**
1. `src/tools/your_tool.py` — implement the function
2. `src/orchestrator/tool_registry.py` — register it with name + description
3. That's it. The ReAct loop auto-discovers registered tools.

---

## Implementation Order

Build in this exact order. Each phase is independently testable.

### Phase 1: Foundation + Docker (Day 1)
**Goal:** Bot runs in Docker, connects to MongoDB, responds to `/start`

| # | Task | File(s) |
|---|------|---------|
| 1.1 | Set up project, install dependencies | `pyproject.toml`, `requirements.txt` |
| 1.2 | Create config module | `src/config.py` |
| 1.3 | Create data models | `src/db/models.py` |
| 1.4 | Create database layer | `src/db/database.py` |
| 1.5 | Create basic bot with `/start` handler | `src/bot/handlers.py`, `src/main.py` |
| 1.6 | Docker setup (bot + mongo) | `Dockerfile`, `docker-compose.yml` |
| 1.7 | Test: `docker-compose up`, bot responds to `/start` | Manual test |

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

### Phase 2: ReAct Loop + First Tools (Day 2)
**Goal:** The core agentic loop works. Bot can respond using tool calls.

| # | Task | File(s) |
|---|------|---------|
| 2.1 | LLM client with tool-calling support | `src/llm/client.py` |
| 2.2 | Tool registry + definitions | `src/orchestrator/tool_registry.py` |
| 2.3 | Tool executor (safe runner) | `src/orchestrator/tool_executor.py` |
| 2.4 | Implement `get_current_datetime` tool | `src/tools/datetime_tools.py` |
| 2.5 | Implement `get_user_tasks` tool | `src/tools/task_tools.py` |
| 2.6 | Build the ReAct loop in orchestrator | `src/orchestrator/orchestrator.py` |
| 2.7 | System prompt (base) | `prompts/system_base.txt` |
| 2.8 | Wire bot → orchestrator | `src/bot/handlers.py` |
| 2.9 | Test: "سلام", "ساعت چنده؟", "تسک‌هامو نشون بده" | Manual test |

### Phase 3: Task Creation + Multi-Turn (Day 3)
**Goal:** Full create-task flow with ask_user for gathering info

| # | Task | File(s) |
|---|------|---------|
| 3.1 | Implement `create_task` tool | `src/tools/task_tools.py` |
| 3.2 | Implement `calculate_priority` sub-agent tool | `src/tools/priority_tools.py` |
| 3.3 | Implement `ask_user` tool (pause/resume loop) | `src/tools/conversation_tools.py` |
| 3.4 | State manager (save/resume ReAct loop) | `src/orchestrator/state_manager.py` |
| 3.5 | Persian date utilities | `src/utils/persian.py` |
| 3.6 | Test: create task with follow-up questions | Manual test |

### Phase 4: Update, Complete, Delete (Day 4)
**Goal:** Full CRUD. LLM resolves "which task?" by reading DB.

| # | Task | File(s) |
|---|------|---------|
| 4.1 | Implement `update_task` tool | `src/tools/task_tools.py` |
| 4.2 | Implement `complete_task` tool | `src/tools/task_tools.py` |
| 4.3 | Implement `request_task_deletion` tool | `src/tools/task_tools.py` |
| 4.4 | Safety layer (confirmation enforcement) | `src/orchestrator/safety.py` |
| 4.5 | Test: update, complete, delete with disambiguation | Manual test |

### Phase 5: Scheduling & Reminders (Day 5)
**Goal:** Reminders, recurring tasks, due-date alerts

| # | Task | File(s) |
|---|------|---------|
| 5.1 | Set up APScheduler with MongoDB store | `src/tools/scheduling_tools.py` |
| 5.2 | Implement `set_reminder` tool | `src/tools/scheduling_tools.py` |
| 5.3 | Implement recurring task triggers | `src/tools/scheduling_tools.py` |
| 5.4 | Due-date alert system | `src/tools/scheduling_tools.py` |
| 5.5 | Test: "فردا بهم بگو..." → receive reminder next day | Manual test |

### Phase 6: User Config + Polish (Day 6)
**Goal:** User preferences, error handling, fallback mode

| # | Task | File(s) |
|---|------|---------|
| 6.1 | Implement `get_user_config` + `update_user_config` tools | `src/tools/config_tools.py` |
| 6.2 | Priority prompt integration | `src/orchestrator/orchestrator.py` |
| 6.3 | Rate limiting middleware | `src/bot/middleware.py` |
| 6.4 | Prompt-based tool calling fallback (for models without native support) | `src/llm/fallback.py` |
| 6.5 | Error handling & graceful recovery | Throughout |
| 6.6 | Structured logging | `src/utils/logging.py` |

### Phase 7: Testing + Docs (Day 7)
**Goal:** Tests, README, final polish

| # | Task | File(s) |
|---|------|---------|
| 7.1 | Unit tests for each tool | `tests/test_tools/` |
| 7.2 | Integration tests for ReAct loop | `tests/test_orchestrator.py` |
| 7.3 | Safety layer tests | `tests/test_safety.py` |
| 7.4 | E2E test with real LLM | `tests/test_e2e.py` |
| 7.5 | README with setup instructions | `README.md` |
| 7.6 | Docker hardening (non-root, read-only, resource limits) | `Dockerfile`, `docker-compose.yml` |

---

## Key Implementation Details

### main.py — Entry Point

```python
import asyncio
from src.config import settings
from src.db.database import Database
from src.llm.client import LLMClient
from src.orchestrator.orchestrator import Orchestrator
from src.orchestrator.tool_executor import ToolExecutor
from src.bot.handlers import create_bot
from src.tools.scheduling_tools import SchedulerService

async def main():
    # 1. Connect to MongoDB
    db = Database(settings.MONGO_URI, settings.MONGO_DB_NAME)
    await db.setup_indexes()

    # 2. Create LLM client (with tool-calling support)
    llm = LLMClient(model=settings.LLM_MODEL, base_url=settings.LLM_BASE_URL)

    # 3. Create scheduler
    scheduler = SchedulerService(settings.MONGO_URI, settings.MONGO_DB_NAME)

    # 4. Create the orchestrator (the brain)
    orchestrator = Orchestrator(db=db, llm=llm, scheduler=scheduler)

    # 5. Create and start Telegram bot (thin layer, delegates to orchestrator)
    bot = create_bot(settings.TELEGRAM_BOT_TOKEN, orchestrator)

    # 6. Start scheduler
    await scheduler.start(bot)

    # 7. Run bot (polling mode)
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
```

### Dependency Injection Pattern

No DI framework. Simple constructor injection:

```python
class Orchestrator:
    def __init__(self, db: Database, llm: LLMClient, scheduler: SchedulerService):
        self.db = db
        self.llm = llm
        self.scheduler = scheduler
        self.tool_executor = ToolExecutor(db, llm, scheduler)  # Runs tools safely
        self.state_manager = StateManager(db)                   # FSM + ReAct state
        self.safety = SafetyLayer()                             # Confirmation, limits
```

### Tool Base Pattern

Each tool is a simple async function registered in the Tool Registry:

```python
# src/tools/task_tools.py

async def get_user_tasks(user_id: str, db: Database,
                         status: str = "pending", category: str = None,
                         due_date_from: str = None, **kwargs) -> dict:
    """Fetch user's tasks with optional filters."""
    filters = {"user_id": user_id}
    if status != "all":
        filters["status"] = status
    # ... build query ...
    tasks = await db.tasks.find(filters).to_list()
    return {"count": len(tasks), "tasks": [...]}
```

```python
# src/orchestrator/tool_registry.py

TOOL_REGISTRY = {
    "get_user_tasks": {
        "function": task_tools.get_user_tasks,
        "description": "Fetch user's tasks with optional filters.",
        "parameters": { ... },   # OpenAI function-calling schema
        "side_effects": False,
    },
    # ... all other tools ...
}
```

### Adding a New Tool (Contributor Guide)

To add a new tool (e.g., a "suggest_tasks" tool):

1. **Create tool function:** `src/tools/suggestion_tools.py`
   ```python
   async def suggest_tasks(user_id: str, db: Database, llm: LLMClient) -> dict:
       """Sub-agent: uses LLM to suggest tasks based on patterns."""
       existing = await db.tasks.find({"user_id": user_id}).to_list()
       prompt = f"Based on these tasks, suggest new ones: {existing}"
       result = await llm.call_simple([{"role": "user", "content": prompt}])
       return json.loads(result)
   ```
2. **Register in tool registry:** `src/orchestrator/tool_registry.py`
   ```python
   "suggest_tasks": {
       "function": suggestion_tools.suggest_tasks,
       "description": "Suggest new tasks based on user's patterns and habits.",
       "parameters": {},
       "side_effects": False,
   }
   ```
3. **Done.** The Planner LLM will see the new tool in its toolbox and call it when appropriate. No changes to the orchestrator, no new prompts needed.

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
    # SECURITY: non-root, read-only filesystem, resource limits
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
    networks:
      - bot_net
    volumes:
      - ./prompts:/app/prompts:ro  # Read-only, hot-reload without rebuild

  mongo:
    image: mongo:7
    # NO ports exposed to host — only reachable within bot_net
    volumes:
      - mongo_data:/data/db
    networks:
      - bot_net

  # Optional: Ollama for local LLM (uncomment if using local models)
  # ollama:
  #   image: ollama/ollama
  #   volumes:
  #     - ollama_data:/root/.ollama
  #   networks:
  #     - bot_net
  #   deploy:
  #     resources:
  #       reservations:
  #         devices:
  #           - capabilities: [gpu]

networks:
  bot_net:
    driver: bridge

volumes:
  mongo_data:
  # ollama_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r botuser && useradd -r -g botuser -u 1000 botuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY prompts/ prompts/

# Run as non-root
USER botuser

CMD ["python", "-m", "src.main"]
```

### Why Docker Matters for an Agentic Bot

The bot is controlled by an LLM that decides which tools to call. Even though our tools
are well-typed Python functions (not arbitrary shell commands), Docker provides defense-in-depth:

| Threat | Docker Mitigation |
|--------|------------------|
| LLM-triggered code execution bug | Read-only filesystem, non-root user |
| Runaway loop consuming resources | CPU/memory limits |
| Accessing host filesystem | Container isolation |
| Reaching internal network services | Docker network isolation — bot can only reach Mongo + LLM |
| Prompt injection leaking system data | No secrets on filesystem, env vars are minimal |

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
