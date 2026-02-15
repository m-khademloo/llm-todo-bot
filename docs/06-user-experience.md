# 06 - User Experience, i18n, Configuration & Conversation Flows

## Telegram UX Philosophy

Telegram bots can have inline keyboards, reply keyboards, menus, etc. We intentionally avoid all of that. The UX is **pure text conversation** — like talking to a smart friend who manages your tasks.

### Why No Buttons?
- Users with 100+ tasks can't navigate buttons
- Natural language is faster than tapping through menus
- The LLM handles ambiguity better than a menu tree ever could
- Simpler code, fewer edge cases
- Users already know how to text — zero learning curve

### The Only Exceptions
- `/start` — Universal reset, required by Telegram
- `/help` — Show brief help text
- `/tasks` — Quick shortcut for "لیست تسک‌ها"
- `/cancel` — Cancel current flow (same as /start but doesn't show welcome)

---

## Conversation Flow Patterns

### Pattern 1: Happy Path (Single-Turn Task Creation)

User provides enough info in one message.

```
User: فردا ساعت ۱۰ جلسه با تیم فنی دارم، حدود ۱ ساعت طول میکشه
Bot:  ✅ تسک اضافه شد!
      📝 جلسه با تیم فنی
      📅 فردا ساعت ۱۰ | ⏱ ۱ ساعت | 🏷 کار
      🟠 اولویت: ۲
```

When the LLM extracts all required fields and the data is unambiguous, skip the gathering phase AND the confirmation phase. Respect the user's time.

**Rule:** If `title` + `category` are clear and there's no destructive action, auto-create without confirmation.

### Pattern 2: Multi-Turn Gathering

User gives partial info.

```
User: باید برم دکتر
Bot:  کی باید بری؟
User: فردا
Bot:  ✅ تسک اضافه شد!
      📝 رفتن به دکتر
      📅 فردا | 🏷 سلامت
      🔴 اولویت: ۱
```

- Ask **one question at a time**
- Max **3 follow-up questions**, then proceed with defaults
- If user says something off-topic mid-gathering, **don't lose context** — handle the interruption, then return to gathering

### Pattern 3: Interruption During Gathering

```
User: باید برم دکتر
Bot:  کی باید بری؟
User: راستی امروز چیکار دارم؟        ← Interruption!
Bot:  📋 تسک‌های امروز:               ← Handle the query
      🟡 خرید هفتگی — عصر
      
      راستی، داشتی میگفتی دکتر —      ← Return to gathering
      کی باید بری؟
```

**Implementation:** The state machine stays in `gathering_create`. When an interruption is detected (classifier sees `query_tasks` while state is `gathering`), the orchestrator:
1. Handles the interruption (execute query, format result)
2. Appends a reminder about the pending task
3. Does NOT change the FSM state

```python
async def handle_interruption(state: ConversationState, message: str, classification: dict) -> str:
    """Handle a message that interrupts an in-progress flow."""
    
    # Execute the interrupting intent
    interruption_response = await handle_intent(classification, state.user_id)
    
    # Remind about pending flow
    if state.fsm_state == "gathering_create":
        partial = state.context.partial_task
        reminder = f"\n\nراستی، داشتی میگفتی «{partial.get('title', '...')}» — ادامه بدیم؟"
        return interruption_response + reminder
    
    return interruption_response
```

### Pattern 4: Disambiguation

```
User: جلسه رو کنسل کن
Bot:  چند تا جلسه داری، کدومو میگی؟
      ۱. جلسه با تیم فنی (فردا)
      ۲. جلسه هفتگی (پنجشنبه)
      ۳. جلسه با مشتری (شنبه)
User: اولی
Bot:  مطمئنی «جلسه با تیم فنی» رو حذف کنم؟
User: آره
Bot:  ✅ حذف شد
```

**How "اولی" (the first one) is resolved:**
The disambiguation state stores the numbered list. When user responds with a number, ordinal, or position reference:
- "اولی" / "۱" / "یکی" → index 0
- "دومی" / "۲" → index 1
- "آخری" → last item
- Full text match → direct match

```python
ORDINAL_MAP = {
    "اولی": 0, "اول": 0, "یکی": 0, "۱": 0, "1": 0,
    "دومی": 1, "دوم": 1, "۲": 1, "2": 1,
    "سومی": 2, "سوم": 2, "۳": 2, "3": 2,
    "آخری": -1, "آخر": -1,
}
```

### Pattern 5: Confirmation Flow

For destructive actions (delete, bulk operations):

```
User: همه تسک‌های انجام‌شده رو پاک کن
Bot:  ⚠️ ۸ تسک انجام‌شده پیدا شد. مطمئنی همه رو حذف کنم؟
      
      بگو "آره مطمئنم" برای حذف
User: آره مطمئنم
Bot:  ✅ ۸ تسک حذف شد
```

**Confirmation acceptance patterns:**
- آره / بله / اوکی / باشه / ok / yes → accept
- نه / نچ / بیخیال / no / cancel → reject
- For destructive bulk: require "آره مطمئنم" or "yes I'm sure"

```python
CONFIRMATION_ACCEPT = {"آره", "بله", "اوکی", "باشه", "ok", "yes", "اره", "بعله", "آری"}
CONFIRMATION_REJECT = {"نه", "نچ", "بیخیال", "no", "cancel", "لغو", "ولش"}
CONFIRMATION_STRONG = {"آره مطمئنم", "yes i'm sure", "بله مطمئنم"}  # For destructive bulk
```

### Pattern 6: Smalltalk & Help

```
User: سلام
Bot:  سلام! 👋 چه کاری برات انجام بدم؟

User: چیکار میتونی بکنی؟
Bot:  من دستیار مدیریت تسک‌هاتم! میتونم:
      📝 تسک جدید اضافه کنم
      📋 لیست تسک‌هاتو نشون بدم
      ✅ تسک‌ها رو تکمیل کنم
      🗑 تسک‌ها رو حذف کنم
      🔔 یادآوری تنظیم کنم
      ⚙️ اولویت‌هاتو تنظیم کنم
      
      فقط کافیه بگی چی میخوای!

User: ممنون
Bot:  خواهش میکنم! 😊 اگه کاری داشتی بگو
```

### Pattern 7: User Configuration

```
User: اولویت منو اینجوری تنظیم کن: ۱. سلامت ۲. کار ۳. خانواده ۴. یادگیری
Bot:  ✅ اولویت‌بندی ذخیره شد!
      ۱. سلامت 🏥
      ۲. کار 💼
      ۳. خانواده 👨‍👩‍👧‍👦
      ۴. یادگیری 📚
      
      از الان تسک‌ها بر این اساس اولویت‌بندی میشن

User: ساعت خاموشی: ۱۱ شب تا ۷ صبح
Bot:  ✅ ساعت خاموشی تنظیم شد (۲۳:۰۰ تا ۰۷:۰۰)
      توی این ساعت‌ها بهت پیام نمیدم
```

---

## Multi-Language Support (i18n)

### Strategy: LLM-Native i18n

We do NOT use traditional i18n files (`.po`, `.json` translation files) for user-facing messages. Instead:

1. **The LLM responds in the user's language** — if user writes in Persian, bot responds in Persian. If user writes in English, bot responds in English.
2. **System messages** (error messages, help text) use simple template strings with language variants.
3. **The bot detects language** from the first message and stores it in user config.

### Why Not Traditional i18n?

- We only have ~100 users
- LLM-generated responses are more natural than template translations
- Supporting a new language requires zero code changes
- Persian has many informal/colloquial variations that templates can't handle

### What We DO Template

Some messages are always the same and don't need LLM creativity:

```python
TEMPLATES = {
    "fa": {
        "welcome": "سلام! 👋 من دستیار مدیریت تسک‌هات هستم. بگو چیکار کنم!",
        "help": "...",
        "error_generic": "یه مشکل فنی پیش اومده 🔧 لطفا دوباره امتحان کن",
        "error_rate_limit": "یکم آروم‌تر! ⏳ لطفا چند ثانیه صبر کن",
        "no_tasks": "🎉 هیچ تسکی نداری! وقت استراحته",
        "task_created": "✅ تسک اضافه شد!",
        "task_deleted": "✅ تسک حذف شد",
        "task_completed": "✅ تسک تکمیل شد",
        "confirm_delete": "مطمئنی میخوای این تسکو حذف کنی؟ (آره / نه)",
    },
    "en": {
        "welcome": "Hi! 👋 I'm your task management assistant. Tell me what to do!",
        "help": "...",
        "error_generic": "Something went wrong 🔧 Please try again",
        "error_rate_limit": "Slow down! ⏳ Please wait a few seconds",
        "no_tasks": "🎉 No tasks! Time to relax",
        "task_created": "✅ Task added!",
        "task_deleted": "✅ Task deleted",
        "task_completed": "✅ Task completed",
        "confirm_delete": "Are you sure you want to delete this task? (yes / no)",
    },
}

def t(key: str, lang: str = "fa") -> str:
    """Get a template string in the user's language."""
    return TEMPLATES.get(lang, TEMPLATES["fa"]).get(key, TEMPLATES["fa"][key])
```

### Language Detection

```python
async def detect_language(message: str) -> str:
    """Detect if message is Persian or English (or other)."""
    # Simple heuristic: check for Persian Unicode range
    persian_chars = sum(1 for c in message if '\u0600' <= c <= '\u06FF')
    total_alpha = sum(1 for c in message if c.isalpha())
    
    if total_alpha == 0:
        return "fa"  # Default
    
    if persian_chars / total_alpha > 0.5:
        return "fa"
    return "en"
```

---

## User Configuration System

### Config Fields

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `language` | `str` | `"fa"` | Response language |
| `timezone` | `str` | `"Asia/Tehran"` | User's timezone |
| `priority_prompt` | `str\|null` | `null` | Custom priority ordering |
| `default_category` | `str` | `"personal"` | Default category for ambiguous tasks |
| `notification_enabled` | `bool` | `true` | Receive reminders? |
| `quiet_hours.enabled` | `bool` | `false` | Quiet hours on/off |
| `quiet_hours.start` | `str` | `"23:00"` | Quiet hours start |
| `quiet_hours.end` | `str` | `"07:00"` | Quiet hours end |
| `daily_summary` | `bool` | `false` | Get daily task summary at 8 AM? |
| `auto_confirm_create` | `bool` | `true` | Skip confirmation for new tasks? |

### How Config is Changed

Config changes go through the same LLM pipeline:

1. **Classifier** detects `set_config` intent
2. **LLM extracts** which setting to change and the new value
3. **Bot confirms** the change
4. **Executor** updates MongoDB

The LLM prompt for config handling:
```
The user wants to change a setting. Extract:
- config_key: which setting (priority_prompt, language, timezone, quiet_hours, etc.)
- config_value: the new value

User's current config:
{current_config}

User said: "{message}"
```

### Priority Prompt — Deep Dive

The `priority_prompt` is the most important config. When user says:
"اولویت من: ۱. سلامت ۲. کار ۳. خانواده ۴. یادگیری"

We store it as a natural-language instruction that gets injected into the Priority Agent's system prompt:

```python
async def build_priority_prompt(user: User) -> str:
    """Build the priority calculation prompt with user's preferences."""
    
    base_prompt = """Calculate priority (1=highest, 5=lowest) for this task.
Consider: due date urgency, category importance, time sensitivity."""
    
    if user.priority_prompt:
        base_prompt += f"""

USER'S PRIORITY PREFERENCES:
{user.priority_prompt}

Follow the user's ordering strictly. For example, if they say Health > Work,
a health task should ALWAYS have equal or higher priority than a work task
(unless the work task is extremely urgent and the health task has no deadline).
"""
    
    return base_prompt
```

This means the priority calculation is **non-deterministic by design** — the LLM weighs multiple factors. But the user's explicit ordering is the strongest signal.

---

## Confusion Handling

### When the Bot is Confused

```
Scenario 1: Truly unclear message

User: بزن
Bot:  چی رو بزنم؟ 🤔
      - یه تسک جدید اضافه کنم؟
      - یه تسکی رو حذف کنم؟
      - یه چیز دیگه؟
```

```
Scenario 2: Ambiguous reference

User: اونو عوض کن
Bot:  کدوم تسکو میگی؟ آخرین تسک‌هات اینا بودن:
      ۱. جلسه با تیم فنی
      ۲. رفتن به دکتر
      ۳. خرید هفتگی
```

```
Scenario 3: Conflicting info

User: فردا ساعت ۳ جلسه دارم ولی قبلش هم جلسه بود
Bot:  الان جلسه فردا ساعت ۳ رو اضافه کنم دیگه؟ 
      اگه جلسه قبلی رو هم میخوای عوض کنی، بگو کدومو
```

### Confusion Resolution Strategy

```python
class ConfusionHandler:
    """Handles ambiguous and unclear messages."""

    async def handle(self, message: str, state: ConversationState, 
                     classification: dict) -> str:
        confidence = classification.get("confidence", 0)
        intent = classification.get("intent", "unclear")

        # Case 1: Very low confidence (< 0.5)
        if confidence < 0.5:
            return await self.ask_what_they_mean(message)

        # Case 2: Multiple possible intents
        if intent == "unclear" and "alternatives" in classification:
            return await self.present_alternatives(classification["alternatives"])

        # Case 3: Intent clear but task reference is ambiguous
        if classification.get("task_reference") and not classification.get("task_id"):
            return await self.disambiguate_task(
                state.user_id, 
                classification["task_reference"]
            )

        # Case 4: Fallback
        return "متوجه نشدم 🤔 میشه واضح‌تر بگی چیکار کنم؟"
```

### Never Guess on Destructive Actions

Even if the bot is 90% sure which task to delete, it ALWAYS confirms:

```python
async def handle_delete(state, classification):
    # Even with high confidence, ALWAYS confirm
    task = await identify_task(state.user_id, classification)
    if task:
        return (
            f"مطمئنی میخوای این تسکو حذف کنی؟\n\n"
            f"📝 {task.title}\n"
            f"📅 {format_date(task.due_date)}\n\n"
            f"بگو آره یا نه"
        )
```

---

## Telegram Message Formatting

### Rules
1. **No HTML, no Markdown V2** — Use simple Markdown (`*bold*`, plain text)
2. **Keep messages under 4096 chars** (Telegram limit)
3. **Use emojis sparingly** — they help scanning, but don't overdo it
4. **One task per line** in lists
5. **RTL is handled by Telegram** — no special handling needed for Persian

### Message Templates

**Task card (detailed):**
```
📌 *{title}*
📅 {due_date} | ⏱ {estimated_time} | 🏷 {category}
{priority_emoji} اولویت: {priority}
{description if exists}
```

**Task list item (compact):**
```
{priority_emoji} {title} — {due_date_short}
```

**Priority emojis:**
```python
PRIORITY_EMOJI = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}
```

**Category emojis:**
```python
CATEGORY_EMOJI = {
    "health": "🏥", "work": "💼", "family": "👨‍👩‍👧‍👦",
    "learning": "📚", "personal": "🏠", "other": "📌",
}
```

### Long Lists (Pagination)

If a query returns more than 10 tasks, show 10 and add:
```
... و ۵ تسک دیگه

بگو "بیشتر" برای دیدن بقیه
```

```python
MAX_TASKS_PER_MESSAGE = 10

async def format_task_list(tasks: list[Task], lang: str = "fa") -> str:
    if not tasks:
        return t("no_tasks", lang)
    
    shown = tasks[:MAX_TASKS_PER_MESSAGE]
    remaining = len(tasks) - len(shown)
    
    lines = [f"📋 {len(tasks)} تسک:\n"]
    for task in shown:
        emoji = PRIORITY_EMOJI[task.priority]
        date_str = format_date_short(task.due_date) if task.due_date else ""
        lines.append(f"{emoji} {task.title}{' — ' + date_str if date_str else ''}")
    
    if remaining > 0:
        lines.append(f"\n... و {remaining} تسک دیگه")
        lines.append('بگو "بیشتر" برای دیدن بقیه')
    
    return "\n".join(lines)
```

---

## Persian Date Display

### Using `jdatetime` for Jalali Calendar

All dates shown to Persian users use the Jalali (Solar Hijri) calendar:

```python
import jdatetime

def format_date_persian(dt: datetime) -> str:
    """Format datetime for Persian display using Jalali calendar."""
    if dt is None:
        return ""
    
    jdt = jdatetime.datetime.fromgregorian(datetime=dt)
    today = jdatetime.datetime.now()
    delta = (jdt.date() - today.date()).days
    
    if delta == 0:
        return "امروز"
    elif delta == 1:
        return "فردا"
    elif delta == 2:
        return "پس‌فردا"
    elif delta == -1:
        return "دیروز"
    elif 0 < delta <= 7:
        weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        return weekdays[jdt.weekday()]
    else:
        months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        return f"{jdt.day} {months[jdt.month - 1]}"


def format_date_short(dt: datetime) -> str:
    """Short date for compact lists."""
    if dt is None:
        return ""
    
    persian = format_date_persian(dt)
    
    # Add time if it's set (not midnight)
    if dt.hour != 0 or dt.minute != 0:
        jdt = jdatetime.datetime.fromgregorian(datetime=dt)
        persian += f" ساعت {jdt.hour}:{jdt.minute:02d}"
    
    return persian
```

---

## Persian Number Handling

```python
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ENGLISH_DIGITS = "0123456789"

def persian_to_int(s: str) -> int:
    """Convert Persian number string to int."""
    translated = s.translate(str.maketrans(PERSIAN_DIGITS, ENGLISH_DIGITS))
    return int(translated)

def int_to_persian(n: int) -> str:
    """Convert int to Persian number string."""
    return str(n).translate(str.maketrans(ENGLISH_DIGITS, PERSIAN_DIGITS))
```

---

## Daily Summary (Optional Feature)

Users can opt-in to a daily morning summary at 8 AM:

```
🌅 صبح بخیر! تسک‌های امروزت:

🔴 جلسه با مدیر — ساعت ۱۰
🟠 ارسال گزارش — تا ظهر
🟡 چشم‌پزشکی — ساعت ۳

و ۲ تسک بدون تاریخ مشخص:
🟢 خرید کتاب پایتون
⚪ مرتب کردن عکس‌ها

روز خوبی داشته باشی! 💪
```

This is a scheduled job that runs daily at 8 AM user-local-time:

```python
async def send_daily_summary(user_id: str):
    user = await db.get_user(user_id)
    if not user.daily_summary:
        return
    
    tz = pytz.timezone(user.timezone)
    today_start = datetime.now(tz).replace(hour=0, minute=0, second=0)
    today_end = today_start + timedelta(days=1)
    
    todays_tasks = await db.query_tasks(user_id, TaskFilter(
        status="pending",
        due_date_range={"from": today_start, "to": today_end},
    ))
    
    undated_tasks = await db.query_tasks(user_id, TaskFilter(
        status="pending",
        has_due_date=False,
    ))
    
    message = format_daily_summary(todays_tasks, undated_tasks, user.language)
    await bot.send_message(chat_id=user_id, text=message)
```

---

## Rate Limiting

Simple in-memory rate limiter (sufficient for <100 users):

```python
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_per_minute: int = 10):
        self.max_per_minute = max_per_minute
        self.timestamps: dict[str, list[float]] = defaultdict(list)
    
    def check(self, user_id: str) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        now = time()
        # Clean old timestamps
        self.timestamps[user_id] = [
            ts for ts in self.timestamps[user_id] 
            if now - ts < 60
        ]
        
        if len(self.timestamps[user_id]) >= self.max_per_minute:
            return False
        
        self.timestamps[user_id].append(now)
        return True
```

---

## First-Time User Onboarding

When a new user sends their first message (or `/start`):

```
سلام! 👋

من دستیار هوشمند مدیریت تسک‌هاتم.

فقط کافیه بگی چیکار باید بکنی، من اضافه‌اش میکنم، یادآوری میکنم، و اولویت‌بندیش میکنم.

مثلا:
📝 "فردا ساعت ۳ دکتر دارم"
📋 "امروز چیکار دارم؟"
✅ "کار خرید تموم شد"
⚙️ "اولویت من: سلامت > کار > خانواده"

شروع کن! 🚀
```

After onboarding, user config is created with defaults:
```python
async def onboard_user(telegram_user) -> User:
    return await db.get_or_create_user(
        user_id=str(telegram_user.id),
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        telegram_username=telegram_user.username,
        language="fa",  # Default, will be auto-detected
        timezone="Asia/Tehran",
    )
```
