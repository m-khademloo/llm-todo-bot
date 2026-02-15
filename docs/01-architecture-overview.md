# 01 - Architecture Overview

## Vision

A Telegram bot that acts as a **personal AI task-management agent**. Users talk to it in natural language (primarily Persian/Farsi, but any language works). The bot understands intent, gathers missing information through conversation, and manages a structured task database on the user's behalf.

The bot is **not** a thin wrapper around an LLM. It is an **agentic system** where the LLM is the brain, but the execution flows through a well-defined state machine, tool calls, and database operations.

---

## High-Level Architecture

Everything runs inside Docker for isolation and reproducibility.

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram User                          │
└──────────────────────────┬──────────────────────────────────┘
                           │  (message / command)
                           ▼
┌═══════════════════ DOCKER NETWORK ═══════════════════════════┐
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   Telegram Bot Layer                    │  │
│  │  (python-telegram-bot)                                 │  │
│  │  Receives messages, sends responses                    │  │
│  └──────────────────────────┬─────────────────────────────┘  │
│                              │                               │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │               ORCHESTRATOR (Python)                    │  │
│  │  Runs the ReAct loop: Planner → Executor → Observer    │  │
│  │  Enforces safety rules, manages state machine          │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │            ReAct Loop (per message)               │  │  │
│  │  │                                                  │  │  │
│  │  │  PLANNER (LLM) ──► TOOL EXECUTOR ──► OBSERVER   │  │  │
│  │  │       ▲              (Python)           │        │  │  │
│  │  │       └─────────────────────────────────┘        │  │  │
│  │  │                 loops until done                  │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  Available tools:                                      │  │
│  │  get_current_datetime, get_user_tasks, create_task,    │  │
│  │  update_task, complete_task, request_task_deletion,     │  │
│  │  calculate_priority, set_reminder, ask_user,            │  │
│  │  get_user_config, update_user_config                    │  │
│  └───────────────┬────────────────┬───────────────────────┘  │
│                  │                │                           │
│         ┌────────┘       ┌────────┘                          │
│         ▼                ▼                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │   MongoDB    │ │  LLM Client  │ │   Scheduler      │     │
│  │              │ │  (LiteLLM)   │ │  (APScheduler)   │     │
│  │  - tasks     │ │              │ │                  │     │
│  │  - users     │ │  Ollama /    │ │  - Reminders     │     │
│  │  - states    │ │  DeepSeek /  │ │  - Recurring     │     │
│  │  - history   │ │  OpenAI /    │ │  - Due-date      │     │
│  │  - jobs      │ │  any model   │ │    alerts        │     │
│  └──────────────┘ └──────────────┘ └──────────────────┘     │
│                                                              │
└══════════════════════════════════════════════════════════════┘
```

### How the ReAct Loop Works (Simplified)

```
User: "امروز چیکار دارم؟"
  │
  ▼
Orchestrator starts ReAct loop
  │
  ▼
Planner (LLM): "I need to know the date first."
  → calls get_current_datetime()
  ← { jalali: "۲۶ بهمن ۱۴۰۴", iso: "2026-02-15", weekday: "یکشنبه" }
  │
  ▼
Planner (LLM): "Now fetch today's tasks."
  → calls get_user_tasks(due_date_from="2026-02-15", due_date_to="2026-02-15")
  ← { tasks: [{title: "جلسه تیم", priority: 1, ...}, ...] }
  │
  ▼
Planner (LLM): "I have the data. Format and respond."
  → Returns: "📋 تسک‌های امروز (یکشنبه ۲۶ بهمن):\n🔴 جلسه تیم — ساعت ۱۰\n..."
  │
  ▼
Orchestrator: loop done, send response to user
```

---

## Core Design Principles

### 1. LLM-Agnostic via LiteLLM
We use **[LiteLLM](https://github.com/BerriAI/litellm)** as the unified LLM client. It provides a single `completion()` interface that works with:
- OpenAI (`gpt-4o`, `gpt-4o-mini`, ...)
- Ollama (local models like `deepseek-r1`, `llama3`, `qwen2.5`, ...)
- DeepSeek API
- Anthropic, Google, Mistral, and 100+ providers

Configuration is a single env var or config entry:
```python
# .env
LLM_MODEL=ollama/deepseek-r1:14b        # local
# LLM_MODEL=deepseek/deepseek-chat       # DeepSeek API
# LLM_MODEL=gpt-4o-mini                  # OpenAI
# LLM_MODEL=anthropic/claude-3-haiku     # Anthropic
LLM_BASE_URL=http://localhost:11434      # only needed for Ollama
```

### 2. State Machine Persisted in MongoDB
Every user has a conversation state stored in MongoDB. The state machine controls the flow (idle, gathering data, confirming, etc.). If the bot restarts, it picks up exactly where it left off.

### 3. Tool-Calling Agent, Not Scripted Pipeline
The LLM is not called in a hardcoded sequence (classify → resolve → execute). Instead,
the LLM receives a **toolbox** and decides which tools to call and in what order.
The code provides **tools** (get_current_datetime, get_user_tasks, create_task, etc.)
and the LLM provides the **intelligence** to chain them correctly.

The LLM is **blind** without tools — it doesn't know the date, the user's tasks, or
anything about reality. It MUST call tools to see the world.

### 4. Docker-First Deployment
Everything runs in Docker containers for security and reproducibility:
- **Bot container** — runs as non-root, read-only filesystem, resource-limited
- **MongoDB container** — only accessible within Docker network
- **Ollama container** (optional) — for local LLM, with GPU access
- No ports exposed except Telegram API outbound

### 5. Single Process, Simple Scale
Target is <100 users. No need for microservices, message queues, or horizontal scaling. A single Python process handles:
- Telegram webhook/polling
- LLM calls (via tool-calling ReAct loop)
- MongoDB operations
- Scheduled jobs (reminders, recurring tasks)

### 6. Open to Contribution
Adding new functionality = adding a new **tool**. A new contributor:
1. Writes a Python function with typed parameters
2. Registers it in the Tool Registry
3. Adds a description so the LLM knows when/how to use it
4. Done — the Orchestrator and ReAct loop handle the rest automatically

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11+ | Ecosystem, LLM libraries, async support |
| Telegram | `python-telegram-bot` v21+ | Mature, async, well-documented |
| LLM Client | `litellm` | Unified interface for all LLM providers |
| Database | MongoDB via `motor` (async) | Flexible schema, good for document storage |
| Scheduler | `APScheduler` v4 | Cron-like scheduling, persistent job store |
| Config | `pydantic-settings` | Typed config from env vars |
| Logging | `structlog` | Structured JSON logging |
| Testing | `pytest` + `pytest-asyncio` | Standard Python testing |

---

## Data Flow Example

### User says: "باید برم چشم پزشکی" (I need to go to the eye doctor)

```
1. Telegram delivers message to bot
2. Orchestrator loads user state → state = "idle"
3. Orchestrator starts ReAct loop, sends message + system prompt + tools to LLM

4. PLANNER (LLM):
   Thinks: "User wants to go to the eye doctor. This is a new task, category=health.
            I don't know when. Let me ask."
   → calls ask_user(question="کی باید بری چشم‌پزشکی؟", context="gathering_create")

5. ORCHESTRATOR: ask_user detected → save state to MongoDB, send question, STOP.
   State saved: { fsm: "waiting_for_user", context: { messages: [...] } }

--- User replies: "پس‌فردا، حدود ۲ ساعت" ---

6. Orchestrator loads state → "waiting_for_user", resumes ReAct loop with user's reply

7. PLANNER (LLM):
   Thinks: "User said 'day after tomorrow, about 2 hours'. I need today's date."
   → calls get_current_datetime()
   ← { iso: "2026-02-15", jalali: "۲۶ بهمن ۱۴۰۴" }

8. PLANNER (LLM):
   Thinks: "Day after tomorrow = Feb 17. Now calculate priority."
   → calls calculate_priority(title="رفتن به چشم‌پزشکی", category="health", due_date="2026-02-17")
   ← { priority: 1, reasoning: "Health + 2 days away + user prioritizes health" }

9. PLANNER (LLM):
   Thinks: "Priority 1. Create the task."
   → calls create_task(title="رفتن به چشم‌پزشکی", category="health",
                       due_date="2026-02-17T09:00", priority=1,
                       estimated_time_minutes=120)
   ← { task_id: "abc123" }

10. PLANNER (LLM):
    Returns: "✅ تسک اضافه شد!\n📝 رفتن به چشم‌پزشکی\n📅 دوشنبه ۲۸ بهمن\n⏱ ۲ ساعت\n🔴 اولویت: ۱"

11. Orchestrator: loop done → send response, state → idle
```

---

## Security Rules (Hardcoded, Not LLM-Dependent)

These are enforced in code, not by prompt engineering:

1. **No destructive action without confirmation** — Delete and bulk operations always require explicit "yes"
2. **User isolation** — Every DB query is scoped to `user_id`. No user can see another user's data.
3. **Prompt injection protection** — System prompts are never overridable by user input. User messages are clearly delimited.
4. **Rate limiting** — Basic rate limiting to prevent abuse (10 messages/minute per user).
5. **No secret leakage** — System prompts, tool definitions, and internal state are never exposed to the user.

---

## What Each Document Covers

| Document | Content |
|----------|---------|
| `01-architecture-overview.md` | This file. High-level design, tech stack, principles |
| `02-agentic-design.md` | LLM orchestration, agents, tools, prompt engineering |
| `03-database-and-state-machine.md` | MongoDB collections, schemas, FSM states & transitions |
| `04-task-lifecycle.md` | Task CRUD, classification, priority, categories |
| `05-scheduling-and-reminders.md` | Reminders, recurring tasks, due-date notifications |
| `06-user-experience.md` | i18n, user config, conversation flows, UX patterns |
| `07-project-structure.md` | Directory layout, module guide, implementation order |
