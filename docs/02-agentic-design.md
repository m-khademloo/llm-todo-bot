# 02 - Agentic LLM Design

## The Core Problem

The LLM is **blind**. It doesn't know:
- What time it is
- What day it is
- What tasks the user has
- What the user's preferences are
- What happened in previous conversations

It's a brain in a jar. To be useful, it needs **tools** — functions it can call to
interact with reality. And it needs an **Orchestrator** to manage the loop of
thinking → calling tools → observing results → thinking again.

---

## Architecture: Planner → Executor → Observer (ReAct Loop)

We use the **ReAct** (Reasoning + Acting) pattern. Instead of hardcoded agent sequences,
the LLM gets a toolbox and **decides for itself** what to do.

```
┌──────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                           │
│                   (Python, runs the loop)                     │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                     ReAct Loop                           │ │
│  │                                                         │ │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────────┐     │ │
│  │   │ PLANNER  │───►│ EXECUTOR │───►│  OBSERVER    │──┐  │ │
│  │   │ (LLM)    │    │ (Python) │    │  (feed back) │  │  │ │
│  │   │          │    │          │    │              │  │  │ │
│  │   │ Thinks:  │    │ Runs the │    │ Adds tool    │  │  │ │
│  │   │ "I need  │    │ tool     │    │ result to    │  │  │ │
│  │   │ to call  │    │ safely   │    │ conversation │  │  │ │
│  │   │ tool X"  │    │          │    │              │  │  │ │
│  │   └──────────┘    └──────────┘    └──────────────┘  │  │ │
│  │        ▲                                            │  │ │
│  │        └────────────────────────────────────────────┘  │ │
│  │                    (loop until done)                    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  SAFETY LAYER (enforced by code, not by LLM):                │
│  ├── Max 8 tool calls per message (prevent infinite loops)   │
│  ├── Destructive tools require user confirmation             │
│  ├── All DB queries scoped to user_id                        │
│  ├── State machine controls multi-turn flows                 │
│  └── Docker isolation prevents system-level damage           │
└──────────────────────────────────────────────────────────────┘
```

### How it differs from the old design

| Old (Hardcoded Agent Sequence) | New (Tool-Calling ReAct Loop) |
|-------------------------------|-------------------------------|
| We decide in Python: "call Classifier, then Resolver, then Executor" | LLM decides: "I need to check the time, then fetch tasks, then respond" |
| Separate agents: Classifier, Resolver, Gatherer, Priority, Formatter | ONE Planner LLM with access to tools |
| Can't handle novel situations we didn't code for | LLM chains tools creatively for any situation |
| Each agent has its own prompt | One unified system prompt + tool descriptions |
| Fixed 2-4 LLM calls per message | LLM calls as many tools as needed, then responds |

---

## The Tool Registry

The Planner LLM has access to these tools. Each tool is a **well-defined Python function**
with typed parameters. The LLM does NOT run arbitrary shell commands — it calls
structured tools through a controlled interface.

### Available Tools

```python
TOOL_REGISTRY = {

    # ─── WORLD AWARENESS ───────────────────────────────────────
    "get_current_datetime": {
        "description": "Get the current date and time in the user's timezone. "
                       "ALWAYS call this first when the user mentions relative dates "
                       "like 'tomorrow', 'next week', 'in 3 days'.",
        "parameters": {},
        "returns": "{ datetime, timezone, weekday, jalali_date }",
        "side_effects": False,
    },

    # ─── TASK READING ──────────────────────────────────────────
    "get_user_tasks": {
        "description": "Fetch the user's tasks from the database with optional filters. "
                       "Use this to see what tasks exist before updating/deleting/completing. "
                       "Also use this when the user asks 'what do I have today?'",
        "parameters": {
            "status": "str | null ('pending', 'done', 'all'). Default: 'pending'",
            "category": "str | null (filter by category)",
            "due_date_from": "str | null (ISO date, inclusive)",
            "due_date_to": "str | null (ISO date, inclusive)",
            "search_text": "str | null (search in title/description)",
            "sort_by": "str ('priority', 'due_date', 'created_at'). Default: 'priority'",
            "limit": "int. Default: 20",
        },
        "returns": "list of task objects",
        "side_effects": False,
    },

    # ─── TASK WRITING ──────────────────────────────────────────
    "create_task": {
        "description": "Create a new task. Call calculate_priority first to get the priority. "
                       "Only call this when you have at least a title and category.",
        "parameters": {
            "title": "str (required)",
            "description": "str | null",
            "due_date": "str | null (ISO datetime)",
            "category": "str (health, work, family, learning, personal, other)",
            "estimated_time_minutes": "int | null",
            "priority": "int (1-5, from calculate_priority)",
            "reminder_at": "str | null (ISO datetime, when to remind)",
            "recurrence_pattern": "str | null (daily, weekly, monthly, or cron expression)",
        },
        "returns": "{ task_id, title, priority, due_date }",
        "side_effects": True,
    },

    "update_task": {
        "description": "Update an existing task. You MUST know the exact task_id. "
                       "If unsure which task, call get_user_tasks first and ask the user.",
        "parameters": {
            "task_id": "str (required — the exact task ID)",
            "updates": "dict (fields to update: title, description, due_date, category, priority, estimated_time_minutes)",
        },
        "returns": "{ success, updated_task }",
        "side_effects": True,
    },

    "complete_task": {
        "description": "Mark a task as done. You MUST know the exact task_id.",
        "parameters": {
            "task_id": "str (required)",
        },
        "returns": "{ success, task_title }",
        "side_effects": True,
    },

    "request_task_deletion": {
        "description": "Request deletion of task(s). This does NOT delete immediately — "
                       "it triggers a confirmation flow. The user must confirm. "
                       "Use this for single or bulk deletes.",
        "parameters": {
            "task_ids": "list[str] (one or more task IDs to delete)",
            "reason": "str (why — shown to user in confirmation message)",
        },
        "returns": "{ confirmation_requested: true, tasks_to_delete: [...] }",
        "side_effects": True,  # Triggers state change, not actual deletion
    },

    # ─── PRIORITY ──────────────────────────────────────────────
    "calculate_priority": {
        "description": "Calculate priority (1-5) for a task based on user's preferences, "
                       "urgency, and existing tasks. Call this before create_task.",
        "parameters": {
            "title": "str",
            "category": "str",
            "due_date": "str | null (ISO datetime)",
            "existing_task_count_by_priority": "dict | null (optional context)",
        },
        "returns": "{ priority: int, reasoning: str }",
        "side_effects": False,
    },

    # ─── USER CONFIG ───────────────────────────────────────────
    "get_user_config": {
        "description": "Get the user's preferences: priority ordering, language, timezone, "
                       "quiet hours, etc. Call this when you need to personalize behavior.",
        "parameters": {},
        "returns": "{ language, timezone, priority_prompt, quiet_hours, ... }",
        "side_effects": False,
    },

    "update_user_config": {
        "description": "Update a user setting. For priority_prompt, store the user's "
                       "natural language preference (e.g., 'Health > Work > Family').",
        "parameters": {
            "key": "str (priority_prompt, language, timezone, quiet_hours, daily_summary)",
            "value": "any",
        },
        "returns": "{ success, updated_key, new_value }",
        "side_effects": True,
    },

    # ─── SCHEDULING ────────────────────────────────────────────
    "set_reminder": {
        "description": "Set a one-time reminder. The bot will message the user at the specified time.",
        "parameters": {
            "remind_at": "str (ISO datetime — when to remind)",
            "message": "str (what to say to the user)",
            "task_id": "str | null (link to a task, optional)",
        },
        "returns": "{ reminder_id, remind_at }",
        "side_effects": True,
    },

    # ─── CONVERSATION CONTROL ──────────────────────────────────
    "ask_user": {
        "description": "Ask the user a question and STOP. The next user message will be "
                       "the answer. Use this when you need more information to proceed. "
                       "IMPORTANT: After calling this, you MUST stop and wait.",
        "parameters": {
            "question": "str (the question to ask, in the user's language)",
            "context": "str (what you're gathering — stored in state for the next turn)",
        },
        "returns": "{ waiting_for_response: true }",
        "side_effects": True,  # Changes FSM state
    },
}
```

### Why NOT Arbitrary Shell Commands?

The user's insight is correct: real AI agents often use shell commands (`date`, `curl`, etc.)
to interact with the world. But for this project:

1. **Shell commands are too broad** — The LLM might run `rm -rf` or `curl` to arbitrary URLs
2. **We have specific needs** — Date, DB, scheduling. Well-typed tools are safer and faster.
3. **Docker provides isolation** — If the LLM somehow escapes the tool sandbox, Docker contains the damage.
4. **Typed tools = better LLM performance** — LLMs are better at calling well-defined functions than composing shell commands.

We get the **same capability** (knowing the time, querying data) through safe, typed tools.

---

## The Orchestrator — The Loop Runner

The Orchestrator is the **only** piece of code that talks to both the LLM and the tools.
It runs the ReAct loop, enforces safety, and manages state.

```python
class Orchestrator:
    """
    The main loop runner. Receives a user message, runs the Planner LLM
    in a tool-calling loop, and returns the final response.
    """

    def __init__(self, db: Database, llm: LLMClient, scheduler: SchedulerService):
        self.db = db
        self.llm = llm
        self.scheduler = scheduler
        self.tool_executor = ToolExecutor(db, scheduler)  # Runs tools safely
        self.state_machine = StateMachine(db)

    async def handle_message(self, user_id: str, message: str) -> str:
        """Main entry point. One user message → one bot response."""

        # ──── 1. HARD COMMANDS (bypass LLM entirely) ────
        if message.strip() == "/start":
            await self.state_machine.reset(user_id)
            return await self._welcome_message(user_id)
        if message.strip() == "/help":
            return HELP_TEXT
        if message.strip() == "/cancel":
            await self.state_machine.reset(user_id)
            return "لغو شد. چیکار کنم؟"

        # ──── 2. LOAD CONTEXT ────
        state = await self.state_machine.get_state(user_id)
        user = await self.db.get_or_create_user(user_id)
        history = await self.db.get_history(user_id, limit=10)

        # ──── 3. HANDLE PENDING CONFIRMATION ────
        #   If the bot asked "are you sure?" and user is responding:
        if state.fsm_state in ("confirming_delete", "confirming_complete"):
            return await self._handle_confirmation(user_id, message, state)

        # ──── 4. BUILD LLM MESSAGES ────
        system_prompt = await self._build_system_prompt(user)
        messages = self._build_messages(system_prompt, history, message, state)

        # ──── 5. RUN THE ReAct LOOP ────
        response = await self._react_loop(
            user_id=user_id,
            messages=messages,
            state=state,
            max_iterations=8,  # Safety: max 8 tool calls per message
        )

        # ──── 6. SAVE STATE & HISTORY ────
        await self.db.add_message(user_id, "user", message)
        await self.db.add_message(user_id, "assistant", response)

        return response

    async def _react_loop(
        self,
        user_id: str,
        messages: list[dict],
        state: ConversationState,
        max_iterations: int = 8,
    ) -> str:
        """
        The core loop. Call LLM → if it wants tools → execute → feed back → repeat.
        Stop when LLM returns a text response (no tool calls).
        """

        for iteration in range(max_iterations):
            # Call LLM with tool definitions
            llm_response = await self.llm.call_with_tools(
                messages=messages,
                tools=self._get_tool_definitions(user_id),
                temperature=0.3,
            )

            # ── Case A: LLM wants to call tool(s) ──
            if llm_response.tool_calls:
                for tool_call in llm_response.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # SAFETY: inject user_id into every DB tool call
                    tool_args["_user_id"] = user_id

                    # SAFETY: check if tool requires confirmation
                    if self._needs_confirmation(tool_name, tool_args):
                        # Don't execute — transition to confirmation state
                        await self._enter_confirmation(user_id, tool_name, tool_args, state)
                        # Return the confirmation question
                        return self._format_confirmation_question(tool_name, tool_args)

                    # Execute the tool
                    result = await self.tool_executor.execute(tool_name, tool_args)

                    # SPECIAL: ask_user → pause the loop, save state, return question
                    if tool_name == "ask_user":
                        await self._save_agent_state(user_id, messages, state, tool_args)
                        return tool_args["question"]

                    # Feed result back to LLM
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

            # ── Case B: LLM returns a text response (done!) ──
            else:
                final_text = llm_response.content
                await self.state_machine.transition(user_id, "idle")
                return final_text

        # ── Safety: max iterations reached ──
        return "یه مشکلی پیش اومده 🔧 لطفا دوباره امتحان کن"
```

### The Key Insight: One LLM, Many Tools

In the old design, we had 5+ separate agents, each with its own prompt, called in a
hardcoded sequence. Now we have **one Planner LLM** that sees all tools and decides
the sequence itself. This is more powerful because:

**Example: "امروز چیکار دارم؟" (What do I have today?)**

Old design (hardcoded sequence):
```
1. Classifier → intent: query_tasks
2. Resolver → builds filters: { due_date: today, status: pending }
3. DB Read → fetch tasks
4. Formatter → pretty-print
= 3-4 LLM calls, fixed sequence we coded
```

New design (LLM decides):
```
LLM thinks: "User wants today's tasks. I need the current date first."
→ calls get_current_datetime()
← { datetime: "2026-02-15T14:30:00", jalali: "۲۶ بهمن ۱۴۰۴", weekday: "یکشنبه" }
LLM thinks: "Now I can query tasks for today."
→ calls get_user_tasks(due_date_from="2026-02-15", due_date_to="2026-02-15", status="pending")
← [{ title: "جلسه تیم فنی", due: "2026-02-15T10:00", priority: 1, category: "work" }, ...]
LLM thinks: "I have the data. Let me format a nice response in Persian."
→ Returns: "📋 تسک‌های امروز (یکشنبه ۲۶ بهمن):\n\n🔴 جلسه تیم فنی — ساعت ۱۰\n..."
= 1 LLM call with 2 tool uses, sequence decided by LLM
```

**Example: "چشمم خوب شد" (My eye is better)**

```
LLM thinks: "User is saying their eye is better. This probably means an eye-related task
is done. Let me check their tasks."
→ calls get_user_tasks(status="pending")
← [{ id: "a1", title: "رفتن به چشم‌پزشکی", ... }, { id: "b2", title: "جلسه کاری", ... }]
LLM thinks: "Task a1 'going to eye doctor' matches 'my eye is better'. Mark it complete."
→ calls complete_task(task_id="a1")
← { success: true, task_title: "رفتن به چشم‌پزشکی" }
LLM: "✅ تسک «رفتن به چشم‌پزشکی» تکمیل شد! خوشحالم چشمت خوب شده 😊"
```

**Example: "همه تسک‌های یادگیری رو پاک کن" (Delete all learning tasks)**

```
LLM thinks: "User wants to delete learning tasks. Let me find them first."
→ calls get_user_tasks(status="pending")
← [{ id: "a1", title: "کتاب پایتون", cat: "learning" },
    { id: "b2", title: "دوره React", cat: "learning" },
    { id: "c3", title: "جلسه کاری", cat: "work" },
    { id: "d4", title: "خوندن مقاله ML", cat: "personal" }]  ← Note: this is learning but categorized as personal!
LLM thinks: "a1 and b2 are clearly learning. d4 'reading ML paper' is also learning-related
even though it's categorized as personal. But I shouldn't guess — only include the ones
clearly learning. Actually, I should include d4 too since the user said 'all learning tasks'.
But deleting is destructive — I must confirm."
→ calls request_task_deletion(task_ids=["a1", "b2", "d4"], reason="all learning-related tasks")
ORCHESTRATOR intercepts: "This is destructive. Ask confirmation."
← Bot: "⚠️ ۳ تسک یادگیری پیدا شد:\n۱. کتاب پایتون\n۲. دوره React\n۳. خوندن مقاله ML\n\nهمشو پاک کنم؟"
```

---

## The System Prompt — Giving the LLM Context

The system prompt is where we inject everything the LLM needs to know. It's built
dynamically for each message:

```python
async def _build_system_prompt(self, user: User) -> str:
    """Build the system prompt with user-specific context."""

    base = """You are a personal task management assistant on Telegram.
You help the user manage their tasks through natural conversation.

LANGUAGE: Respond in the same language the user writes in (usually Persian/Farsi).

CAPABILITIES:
You have access to tools to interact with the user's task database.
ALWAYS use tools to get real information — NEVER make up dates, tasks, or data.
You are blind to the real world without tools. If you need the date, call get_current_datetime.
If you need to see tasks, call get_user_tasks. NEVER assume.

BEHAVIOR:
1. When user describes a new task → gather info (ask if needed via ask_user) → create_task
2. When user wants to update/complete/delete → get_user_tasks first to find the task → act
3. When user asks about tasks → get_current_datetime + get_user_tasks → format nicely
4. When user changes settings → update_user_config
5. When user is chatting → respond naturally, briefly

CRITICAL RULES:
- NEVER delete without calling request_task_deletion (triggers confirmation)
- NEVER fabricate task data. If unsure, call get_user_tasks.
- NEVER make up the current date/time. Call get_current_datetime.
- If multiple tasks could match, ask the user to clarify (via ask_user or in your response)
- Keep messages SHORT. This is Telegram, not email.
- Use emojis sparingly: 📌 for tasks, ✅ for done, ❌ for errors, 🔔 for reminders
- NEVER expose internal IDs, JSON, or technical details to the user
- For task lists, use this format:
  🔴 *task title* — date
  🟠 *task title* — date
  (🔴=priority 1, 🟠=2, 🟡=3, 🟢=4, ⚪=5)"""

    # Inject user's priority preference if set
    if user.priority_prompt:
        base += f"""

USER'S PRIORITY PREFERENCES:
{user.priority_prompt}
When calculating priority, follow these preferences strictly."""

    # Inject user's language/timezone
    base += f"""

USER INFO:
- Timezone: {user.timezone}
- Language preference: {user.language}"""

    return base
```

### Why One Big Prompt Instead of Many Small Ones?

In the old design, each agent (classifier, resolver, gatherer, etc.) had its own prompt.
In the new design, one prompt covers everything because **the LLM is one agent doing
everything**. The tools provide the structure that used to be in separate agents.

The prompt is long, but the LLM only processes it once per message (not once per agent call).

---

## Tool Executor — The Safe Execution Layer

The Tool Executor runs tools safely. It's pure Python — no LLM involved.

```python
class ToolExecutor:
    """Executes tool calls safely. Every tool is a Python function."""

    def __init__(self, db: Database, scheduler: SchedulerService):
        self.db = db
        self.scheduler = scheduler
        self._tools: dict[str, Callable] = {
            "get_current_datetime": self._get_current_datetime,
            "get_user_tasks": self._get_user_tasks,
            "create_task": self._create_task,
            "update_task": self._update_task,
            "complete_task": self._complete_task,
            "request_task_deletion": self._request_task_deletion,
            "calculate_priority": self._calculate_priority,
            "get_user_config": self._get_user_config,
            "update_user_config": self._update_user_config,
            "set_reminder": self._set_reminder,
            "ask_user": self._ask_user,
        }

    async def execute(self, tool_name: str, args: dict) -> dict:
        """Execute a tool by name. Returns result dict."""
        if tool_name not in self._tools:
            return {"error": f"Unknown tool: {tool_name}"}

        user_id = args.pop("_user_id")  # Always present, injected by orchestrator

        try:
            result = await self._tools[tool_name](user_id=user_id, **args)
            return result
        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
            return {"error": f"Tool {tool_name} failed: {str(e)}"}

    # ─── Tool Implementations ─────────────────────────────────

    async def _get_current_datetime(self, user_id: str) -> dict:
        """Returns current datetime in user's timezone."""
        user = await self.db.get_user(user_id)
        tz = pytz.timezone(user.timezone or "Asia/Tehran")
        now = datetime.now(tz)
        jnow = jdatetime.datetime.fromgregorian(datetime=now)

        weekdays_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        months_fa = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                     "مهر","آبان","آذر","دی","بهمن","اسفند"]

        return {
            "iso": now.isoformat(),
            "timezone": str(tz),
            "jalali_date": f"{jnow.day} {months_fa[jnow.month-1]} {jnow.year}",
            "jalali_weekday": weekdays_fa[jnow.weekday()],
            "gregorian_date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "unix_timestamp": int(now.timestamp()),
        }

    async def _get_user_tasks(self, user_id: str, status: str = "pending",
                               category: str = None, due_date_from: str = None,
                               due_date_to: str = None, search_text: str = None,
                               sort_by: str = "priority", limit: int = 20) -> dict:
        """Fetch tasks from DB with filters."""
        filters = {"user_id": user_id}
        if status != "all":
            filters["status"] = status
        if category:
            filters["category"] = category
        if due_date_from or due_date_to:
            filters["due_date"] = {}
            if due_date_from:
                filters["due_date"]["$gte"] = datetime.fromisoformat(due_date_from)
            if due_date_to:
                filters["due_date"]["$lte"] = datetime.fromisoformat(due_date_to)
        if search_text:
            filters["$text"] = {"$search": search_text}

        tasks = await self.db.tasks.find(filters).sort(sort_by, 1).limit(limit).to_list()

        return {
            "count": len(tasks),
            "tasks": [
                {
                    "task_id": t["task_id"],
                    "title": t["title"],
                    "description": t.get("description"),
                    "due_date": t.get("due_date", "").isoformat() if t.get("due_date") else None,
                    "priority": t["priority"],
                    "category": t["category"],
                    "status": t["status"],
                    "estimated_time_minutes": t.get("estimated_time_minutes"),
                    "created_at": t["created_at"].isoformat(),
                }
                for t in tasks
            ],
        }

    async def _create_task(self, user_id: str, title: str, category: str,
                           priority: int = 3, description: str = None,
                           due_date: str = None, estimated_time_minutes: int = None,
                           reminder_at: str = None, recurrence_pattern: str = None) -> dict:
        """Create a new task."""
        task = Task(
            user_id=user_id,
            title=title,
            category=category,
            priority=priority,
            description=description,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            estimated_time_minutes=estimated_time_minutes,
        )
        await self.db.tasks.insert_one(task.dict())

        # Auto-schedule reminder if due_date is set
        if due_date and reminder_at:
            await self.scheduler.schedule_reminder(
                user_id=user_id,
                task_id=task.task_id,
                remind_at=datetime.fromisoformat(reminder_at),
                message=f"🔔 یادآوری: {title}",
            )

        # Handle recurrence
        if recurrence_pattern:
            await self.scheduler.schedule_recurring(task, recurrence_pattern)

        return {"task_id": task.task_id, "title": title, "priority": priority}

    # ... similar implementations for update_task, complete_task, etc.

    async def _ask_user(self, user_id: str, question: str, context: str = "") -> dict:
        """Signal that we need to ask the user something. Does not send message directly."""
        return {"waiting_for_response": True, "question": question, "context": context}
```

### Tool Safety Properties

Every tool has two key properties:

| Property | Meaning |
|----------|---------|
| `side_effects: False` | Read-only. Can be called freely. (get_current_datetime, get_user_tasks, get_user_config) |
| `side_effects: True` | Modifies data. Orchestrator may intercept. (create_task, update_task, request_task_deletion) |

The Orchestrator uses this to decide whether to intercept:

```python
def _needs_confirmation(self, tool_name: str, args: dict) -> bool:
    """Does this tool call need user confirmation before executing?"""
    # Deletion ALWAYS needs confirmation
    if tool_name == "request_task_deletion":
        return True
    # Bulk operations need confirmation
    if tool_name == "update_task" and len(args.get("task_ids", [])) > 1:
        return True
    # Everything else is fine
    return False
```

---

## LLM Tool Calling via LiteLLM

LiteLLM supports function/tool calling for most providers:

```python
class LLMClient:
    """Unified LLM client with tool-calling support."""

    def __init__(self, model: str, base_url: str | None = None):
        self.model = model
        self.base_url = base_url

    async def call_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Call LLM with tool definitions. Returns response that may include tool_calls."""
        response = await acompletion(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",  # LLM decides whether to call tools
            temperature=temperature,
            max_tokens=max_tokens,
            api_base=self.base_url,
        )
        return response.choices[0].message

    async def call_simple(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> str:
        """Simple call without tools (for sub-agents like priority calculator)."""
        response = await acompletion(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_base=self.base_url,
        )
        return response.choices[0].message.content
```

### Tool Definitions Format (OpenAI-Compatible)

```python
def _get_tool_definitions(self, user_id: str) -> list[dict]:
    """Generate tool definitions in OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "Get current date/time in user's timezone. Call this when you need to know today's date.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_tasks",
                "description": "Fetch user's tasks with optional filters.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pending", "done", "all"], "default": "pending"},
                        "category": {"type": "string", "enum": ["health","work","family","learning","personal","other"]},
                        "due_date_from": {"type": "string", "description": "ISO date"},
                        "due_date_to": {"type": "string", "description": "ISO date"},
                        "search_text": {"type": "string"},
                        "sort_by": {"type": "string", "enum": ["priority","due_date","created_at"]},
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": [],
                },
            },
        },
        # ... all other tools ...
    ]
```

### Models Without Tool Calling Support

Some models (especially small local Ollama models) don't support native tool calling.
For those, we fall back to **prompt-based tool calling**:

```python
class PromptBasedToolCaller:
    """
    Fallback for models without native function calling.
    Wraps tool definitions into the system prompt and parses
    structured JSON responses that indicate tool calls.
    """

    TOOL_PROMPT_SUFFIX = """
AVAILABLE TOOLS:
You can call tools by responding with a JSON block:
```json
{"tool": "tool_name", "args": {"param1": "value1"}}
```

If you want to respond to the user directly (no tool call), just write your message normally.
If you need to call a tool, respond ONLY with the JSON block, nothing else.

{tool_descriptions}
"""

    async def call_with_tools(self, messages, tools, **kwargs):
        # Inject tool descriptions into system prompt
        # Parse response for JSON tool calls
        # Return in same format as native tool calling
        ...
```

This means the bot works with:
- **OpenAI / Anthropic / DeepSeek API** → native tool calling
- **Ollama local models** → prompt-based fallback (works but slightly less reliable)

---

## Multi-Turn Conversations: The `ask_user` Tool

The hardest part of the ReAct loop is **pausing**. When the LLM needs more info from
the user, the loop must:
1. Save its state (conversation messages, partial results)
2. Send the question to the user
3. Wait for the user to respond
4. Resume from where it left off

### How It Works

```
Turn 1:
  User: "یه تسک جدید اضافه کن"
  LLM thinks: "User wants to add a task but didn't say what."
  → calls ask_user(question="چه تسکی میخوای اضافه کنی؟", context="gathering_create")
  ORCHESTRATOR: saves state, sends question, STOPS

Turn 2:
  User: "جلسه با مدیر فردا ساعت ۱۰"
  ORCHESTRATOR: loads saved state, sees context="gathering_create"
  Resumes LLM with: [prev messages] + [tool result: {user_said: "جلسه با مدیر فردا ساعت ۱۰"}]
  LLM thinks: "Now I have the info. Let me get the date and create the task."
  → calls get_current_datetime()
  ← { iso: "2026-02-15T...", ... }
  → calls calculate_priority(title="جلسه با مدیر", category="work", due_date="2026-02-16T10:00")
  ← { priority: 2, reasoning: "..." }
  → calls create_task(title="جلسه با مدیر", category="work", due_date="2026-02-16T10:00", priority=2)
  ← { task_id: "abc123", ... }
  LLM: "✅ تسک اضافه شد!\n📝 جلسه با مدیر\n📅 فردا ساعت ۱۰\n🟠 اولویت: ۲"
```

### State Persistence for Multi-Turn

```python
async def _save_agent_state(self, user_id: str, messages: list[dict],
                            state: ConversationState, tool_args: dict):
    """Save the ReAct loop state so we can resume on next message."""
    state.fsm_state = "waiting_for_user"
    state.context = {
        "messages": messages,           # Full LLM conversation so far
        "ask_context": tool_args.get("context", ""),
        "turn_count": state.context.get("turn_count", 0) + 1,
    }
    await self.state_machine.save(user_id, state)

async def _resume_agent(self, user_id: str, user_reply: str,
                        state: ConversationState) -> str:
    """Resume the ReAct loop with the user's response."""
    messages = state.context["messages"]

    # Inject the user's reply as the tool result
    messages.append({
        "role": "tool",
        "content": json.dumps({
            "user_response": user_reply,
            "context": state.context.get("ask_context", ""),
        }, ensure_ascii=False),
    })

    # Continue the ReAct loop
    return await self._react_loop(
        user_id=user_id,
        messages=messages,
        state=state,
        max_iterations=8 - state.context.get("turn_count", 0),  # Shrinking budget
    )
```

---

## Sub-Agents: When One LLM Call Isn't Enough

Some tools internally use LLM calls. These are **sub-agents** — the Planner calls a tool,
and that tool uses the LLM for its own reasoning. The Planner doesn't know or care.

### Sub-Agent: Priority Calculator

The `calculate_priority` tool internally uses an LLM call:

```python
async def _calculate_priority(self, user_id: str, title: str, category: str,
                               due_date: str = None, **kwargs) -> dict:
    """Sub-agent: uses LLM to calculate priority."""

    user = await self.db.get_user(user_id)
    existing_tasks = await self.db.tasks.find(
        {"user_id": user_id, "status": "pending"}
    ).to_list()

    prompt = f"""Calculate priority 1-5 for this task.
1=most urgent, 5=least.

Task: {title}
Category: {category}
Due: {due_date or 'not set'}

User's priority preferences:
{user.priority_prompt or 'No specific preferences. Use common sense.'}

Existing tasks: {len(existing_tasks)} pending tasks.
Priority distribution: {Counter(t['priority'] for t in existing_tasks)}

Respond with JSON: {{"priority": N, "reasoning": "..."}}"""

    result = await self.llm.call_simple(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return json.loads(result)
```

### Architecture: Main LLM vs Sub-Agents

```
User Message
     │
     ▼
┌────────────────┐
│ MAIN LLM       │  ← One LLM (the Planner), runs in ReAct loop
│ (Planner)      │
│                │
│ Tool calls:    │
│ ├── get_current_datetime()     ← Pure Python (no LLM)
│ ├── get_user_tasks()           ← Pure Python (DB query)
│ ├── create_task()              ← Pure Python (DB write)
│ ├── calculate_priority()       ← SUB-AGENT (another LLM call inside!)
│ ├── update_user_config()       ← Pure Python
│ └── ask_user()                 ← Pauses loop, waits for user
│                │
│ Finally:       │
│ Returns text   │  ← The user-facing response
└────────────────┘
```

The Main LLM doesn't know that `calculate_priority` uses LLM internally. It's just a tool
that returns `{priority: 2, reasoning: "..."}`. This is **encapsulation** — sub-agents
are implementation details of tools.

---

## Docker Isolation & Security

### Why Docker?

The bot is an agent that executes actions based on LLM decisions. Even with well-typed tools,
we want defense in depth:

1. **Tool sandbox** — Tools can only access MongoDB and the scheduler. No filesystem, no network.
2. **Resource limits** — CPU/memory limits prevent runaway processes.
3. **No privilege escalation** — Bot runs as non-root user.
4. **Network isolation** — Bot can only reach MongoDB, Ollama/LLM API, and Telegram API.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  bot:
    build: .
    env_file: .env
    depends_on:
      - mongo
    restart: unless-stopped
    # Security: non-root, limited resources
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
      - ./prompts:/app/prompts:ro  # Read-only prompt templates

  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    networks:
      - bot_net
    # No ports exposed to host — only bot can reach it

  # Optional: Ollama for local LLM
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - bot_net
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]  # If you have a GPU

networks:
  bot_net:
    driver: bridge
    internal: false  # Needs internet for Telegram API

volumes:
  mongo_data:
  ollama_data:
```

### Network Security

```
┌─────────────────────────────────────────────┐
│               Docker Network: bot_net        │
│                                              │
│  ┌───────┐    ┌───────┐    ┌──────────┐    │
│  │  Bot  │───►│ Mongo │    │  Ollama  │    │
│  │       │    └───────┘    └──────────┘    │
│  │       │─────────────────────►│           │
│  │       │                                  │
│  └───┬───┘                                  │
│      │                                      │
└──────┼──────────────────────────────────────┘
       │ (only outbound to)
       ▼
   Telegram API (api.telegram.org)
   LLM API (api.openai.com / api.deepseek.com) — if using cloud LLM
```

The bot can **only** reach:
- MongoDB (within Docker network)
- Ollama (within Docker network)
- Telegram API (internet)
- LLM provider API (internet, if using cloud)

It **cannot** reach:
- Host filesystem (read-only container)
- Other services on the host
- Internal network resources

---

## Prompt Management

### File-Based Prompts

The main system prompt is built in code (because it's dynamic per user), but
sub-agent prompts and templates are stored as files:

```
prompts/
├── system_base.txt           # Base system prompt (static parts)
├── priority_calculator.txt   # Sub-agent: priority calculation
├── tool_descriptions.txt     # Tool documentation for prompt-based fallback
└── fallback_responses.txt    # Canned responses for error cases
```

### Prompt Versioning
Since prompts are files, they're tracked in git. Changes are auditable.
Docker mounts them read-only, so they can be updated without rebuilding.

---

## Error Handling

### LLM Returns Garbage Tool Call

```python
try:
    tool_args = json.loads(tool_call.function.arguments)
except json.JSONDecodeError:
    # Feed error back to LLM so it can retry
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": '{"error": "Invalid JSON in tool arguments. Please try again with valid JSON."}',
    })
    continue  # Next iteration of ReAct loop
```

### Tool Execution Fails

```python
result = await self.tool_executor.execute(tool_name, tool_args)
if "error" in result:
    # Feed error back to LLM — it might try a different approach
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result),  # {"error": "Task not found"}
    })
    continue
```

### Max Iterations Reached

If the LLM gets stuck in a loop (calling the same tool repeatedly, or not converging):
1. After 8 iterations: return a friendly error message
2. Log the full conversation for debugging
3. Reset state to idle

### Fallback for Models Without Tool Support

If the LLM provider doesn't support tools at all:

```python
if not self.llm.supports_tools:
    # Fall back to single-call mode: send everything in the system prompt
    # and parse structured JSON from the response
    return await self._fallback_single_call(user_id, message, state)
```

---

## Conversation History & Context

### What Gets Stored Per Message

```python
{
    "user_id": "telegram_id",
    "role": "user | assistant | tool",
    "content": "message text",
    "timestamp": datetime,
    "metadata": {
        "tool_calls": [...],        # if assistant message had tool calls
        "model_used": "deepseek-chat",
        "tokens_used": 450,
        "processing_time_ms": 1200,
    }
}
```

### Context Window for the Planner

The Planner LLM receives:
1. **System prompt** (static + user config)
2. **Last 10 conversation messages** (user + assistant, no internal tool calls)
3. **Current message**
4. **Resumed state** (if continuing multi-turn)

We do NOT send previous tool call details in history — they're verbose and the
Planner can re-call tools if needed. We only send the final user-facing messages.

### History Trimming

```python
async def get_history_for_llm(self, user_id: str, limit: int = 10) -> list[dict]:
    """Get conversation history formatted for LLM context."""
    messages = await self.db.history.find(
        {"user_id": user_id, "role": {"$in": ["user", "assistant"]}},
    ).sort("timestamp", -1).limit(limit).to_list()

    return [
        {"role": m["role"], "content": m["content"]}
        for m in reversed(messages)  # Chronological order
    ]
```

---

## Testing Strategy

### Unit Testing Tools

Each tool is independently testable — it's just a Python function:

```python
async def test_get_current_datetime():
    db = MockDatabase(user={"timezone": "Asia/Tehran"})
    executor = ToolExecutor(db, MockScheduler())
    result = await executor.execute("get_current_datetime", {"_user_id": "test123"})
    assert "iso" in result
    assert "jalali_date" in result

async def test_create_task():
    db = MockDatabase()
    executor = ToolExecutor(db, MockScheduler())
    result = await executor.execute("create_task", {
        "_user_id": "test123",
        "title": "Test",
        "category": "work",
        "priority": 3,
    })
    assert "task_id" in result
```

### Integration Testing the ReAct Loop

```python
async def test_react_loop_query():
    """Test: user asks for today's tasks, LLM calls tools correctly."""
    mock_llm = MockLLM(responses=[
        # First call: LLM wants to get the date
        ToolCallResponse(tool="get_current_datetime", args={}),
        # Second call: LLM wants tasks
        ToolCallResponse(tool="get_user_tasks", args={"due_date_from": "2026-02-15"}),
        # Third call: LLM returns final text
        TextResponse("📋 تسک‌های امروز: ..."),
    ])
    orchestrator = Orchestrator(db=mock_db, llm=mock_llm, scheduler=mock_scheduler)
    result = await orchestrator.handle_message("user123", "امروز چیکار دارم؟")
    assert "📋" in result
```

### End-to-End with Real LLM

```python
@pytest.mark.e2e
async def test_full_task_lifecycle():
    """Uses real LLM + test MongoDB."""
    bot = create_test_bot()
    r1 = await bot.handle("فردا جلسه با مدیر دارم ساعت ۱۰")
    assert "✅" in r1  # Task created
    r2 = await bot.handle("تسک‌هامو نشون بده")
    assert "جلسه" in r2  # Task appears
    r3 = await bot.handle("جلسه تموم شد")
    assert "تکمیل" in r3 or "✅" in r3  # Task completed
```
