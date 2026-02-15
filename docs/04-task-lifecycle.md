# 04 - Task Lifecycle & Classification

## How Messages Are Handled (No Coded Pipeline)

There is **no coded classification pipeline**. Every message goes through the same path:

```
User Message
     │
     ▼
┌─────────────────────┐
│ /start?             │  YES → Reset (the ONLY coded check)
│ (safety command)     │  NO  → Continue
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Saved ReAct context?│  YES → Resume loop (user is replying to ask_user)
│                     │  NO  → Start fresh ReAct loop
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ ReAct Loop          │  LLM decides EVERYTHING:
│ (LLM + tools)       │  - What the user means
│                     │  - Which tools to call
│                     │  - What to ask
│                     │  - How to respond
└─────────────────────┘
```

There is no "classify then route" step. The LLM sees the message, the tools, and
the conversation history, and decides the entire flow itself.

**Why no classifier?** Because classification is just the LLM's first thought.
When it sees "باید برم چشم‌پزشکی", it doesn't output `{intent: "create_task"}` to a
coded router — it thinks "this is a new task" and immediately starts calling
`get_current_datetime()`, `ask_user("کی باید بری؟")`, etc. The classification and
execution happen in one continuous LLM reasoning chain.

---

## What the LLM Understands (Not Coded — Just Examples)

The following are examples of how the LLM interprets messages. None of this is coded
in Python. The LLM handles all of this through its system prompt and reasoning.

### Types of User Messages

#### 1. `create_task` — User wants to add something new

**Trigger patterns:**
- "باید برم ..." (I need to go to ...)
- "یادم باشه ..." (I should remember to ...)
- "فردا ... دارم" (Tomorrow I have ...)
- "اضافه کن ..." (Add ...)
- "یه تسک جدید: ..." (A new task: ...)
- Any sentence describing a future obligation/plan

**Extracted entities:**
```json
{
  "title": "string (main action)",
  "category": "health|work|family|learning|personal|other",
  "due_date_raw": "فردا | پس‌فردا | شنبه | ۲۵ بهمن | ...",
  "time_raw": "ساعت ۳ | عصر | ...",
  "duration_raw": "۲ ساعت | نیم ساعت | ...",
  "priority_raw": "مهمه | فوری | عادیه | ...",
  "recurrence_raw": "هر روز | هفته‌ای | ..."
}
```

#### 2. `update_task` — User wants to change an existing task

**Trigger patterns:**
- "تاریخ چشم‌پزشکی رو عوض کن" (Change the date of the eye doctor)
- "جلسه رو بزن هفته بعد" (Move the meeting to next week)
- "اون تسک یادگیری رو ..." (That learning task ...)

**Extracted entities:**
```json
{
  "task_reference": "string (how user refers to the task)",
  "updates": {
    "field": "new_value"
  }
}
```

#### 3. `delete_task` — User wants to remove a task

**Trigger patterns:**
- "تسک ... رو پاک کن" (Delete the ... task)
- "دیگه نمیخوام ..." (I don't want ... anymore)
- "... رو حذف کن" (Remove ...)
- "بیخیال ..." (Forget about ...)

**Always requires confirmation before execution.**

#### 4. `complete_task` — User reports something is done

**Trigger patterns:**
- "چشمم خوب شد" (My eye is better) → implies eye doctor task is done
- "جلسه تموم شد" (The meeting is done)
- "... رو انجام دادم" (I did ...)
- "تموم شد" (It's done) — needs context from recent messages

#### 5. `query_tasks` — User wants to see their tasks

**Trigger patterns:**
- "امروز چیکار دارم؟" (What do I have today?)
- "تسک‌هامو نشون بده" (Show my tasks)
- "لیست تسک‌ها" (Task list)
- "این هفته چیکار دارم؟" (What do I have this week?)
- "تسک‌های کاری" (Work tasks)

**Query parameters extracted:**
```json
{
  "time_range": "today | tomorrow | this_week | all",
  "category_filter": "work | health | ...",
  "status_filter": "pending | done | all",
  "sort_preference": "priority | date"
}
```

#### 6. `set_config` — User wants to change settings

**Trigger patterns:**
- "اولویت من: سلامت > کار > خانواده" (My priority: health > work > family)
- "زبان رو عوض کن" (Change the language)
- "ساعت خاموشی: ..." (Quiet hours: ...)

#### 7. `smalltalk` — User is chatting, not tasking

**Trigger patterns:**
- "سلام" (Hello)
- "چطوری؟" (How are you?)
- "ممنون" (Thanks)
- "کمک" (Help) — if not `/help`
- "چیکار میتونی بکنی؟" (What can you do?)

#### 8. `unclear` — Bot can't determine intent

**When this happens:**
- Very short messages with no context: "بزن"
- Ambiguous messages: "اون یکی" (that one) without prior context
- Messages that could be multiple intents

**Response:** Ask for clarification, don't guess.

---

## Task Creation Flow (Full Detail)

### Step 1: Initial Classification & Entity Extraction

User: "سه روز دیگه جلسه دارم در مورد پروژه جدید"

Classifier output:
```json
{
  "intent": "create_task",
  "confidence": 0.95,
  "extracted_entities": {
    "title": "جلسه پروژه جدید",
    "category": "work",
    "due_date_raw": "سه روز دیگه",
    "time_raw": null,
    "duration_raw": null,
    "priority_raw": null,
    "recurrence_raw": null
  }
}
```

### Step 2: Date Resolution

Raw dates are converted to absolute dates using a **date resolver**:

```python
from datetime import datetime, timedelta
import jdatetime  # For Jalali/Persian calendar support

class DateResolver:
    """Resolves Persian relative date expressions to absolute dates."""

    RELATIVE_MAP = {
        "امروز": 0,        # today
        "فردا": 1,          # tomorrow
        "پس‌فردا": 2,        # day after tomorrow
        "پسفردا": 2,        # alternate spelling
    }

    def resolve(self, raw: str, reference_date: datetime = None) -> datetime | None:
        ref = reference_date or datetime.now()

        # Check relative dates
        for pattern, days in self.RELATIVE_MAP.items():
            if pattern in raw:
                return ref + timedelta(days=days)

        # Check "X روز دیگه" (in X days)
        match = re.search(r'(\d+|[۰-۹]+)\s*روز\s*دیگه', raw)
        if match:
            days = persian_to_int(match.group(1))
            return ref + timedelta(days=days)

        # Check Persian weekdays
        # Check Jalali dates (e.g., "۲۵ بهمن")
        # Check Gregorian dates

        # Fallback: let LLM interpret
        return None
```

### Step 3: Data Gathering (if needed)

The Data Gatherer checks what's missing and asks follow-ups.

**Required fields strategy:**

| Field | If missing... |
|-------|---------------|
| `title` | Should never be missing (extracted from initial message) |
| `category` | LLM infers from title. If ambiguous, asks. |
| `due_date` | Ask: "کی باید انجامش بدی؟" — if user says "نمیدونم", leave null |
| `estimated_time` | Ask if relevant (meetings, appointments). Skip for simple tasks. |

**Max 3 follow-up questions.** After that, proceed with defaults.

### Step 4: Priority Calculation

Once we have enough data, the Priority Agent calculates priority.

**Priority Scale:**
| Priority | Meaning | Color |
|----------|---------|-------|
| 1 | Critical / Urgent | 🔴 |
| 2 | High | 🟠 |
| 3 | Medium (default) | 🟡 |
| 4 | Low | 🟢 |
| 5 | Someday / Nice to have | ⚪ |

**Priority calculation factors (in order of importance):**

1. **User's priority config** — If user said "Health > Work", a health task starts at priority 1-2
2. **Due date urgency** — Today/tomorrow = boost priority by 1
3. **Explicit priority** — If user said "فوری" (urgent), override to 1
4. **Category default** — Health defaults higher than learning
5. **Relative to existing tasks** — If user has 5 priority-1 tasks, maybe this is a 2

### Step 5: Confirmation

Before saving, show user a summary:

```
📌 تسک جدید:

📝 جلسه پروژه جدید
📅 چهارشنبه ۲۸ بهمن
🏷 کار
🔴 اولویت: ۱ (بالا)

درسته؟ (آره / نه)
```

### Step 6: Execution

On confirmation:
- Save task to MongoDB
- Set up reminder if due_date exists (default: remind at 9 AM on due date)
- Set up recurrence if applicable
- Return success message

---

## Task Update Flow

### Finding the Right Task

User: "جلسه رو بزن هفته بعد" (Move the meeting to next week)

1. **Search by reference:** LLM extracts "جلسه" (meeting) as the task reference
2. **Query pending tasks** with text search
3. **Match results:**
   - 0 matches → "تسکی با این عنوان پیدا نکردم" + list recent tasks
   - 1 match (high confidence) → proceed with update
   - Multiple matches → disambiguate:
     ```
     چند تا جلسه داری، کدومو میگی؟
     ۱. جلسه پروژه جدید (چهارشنبه)
     ۲. جلسه هفتگی تیم (پنجشنبه)
     ```

### Applying Updates

The LLM extracts which field(s) to update:

```json
{
  "task_reference": "جلسه",
  "updates": {
    "due_date_raw": "هفته بعد"
  }
}
```

Date resolver converts "هفته بعد" → actual date. Then confirm with user.

---

## Task Completion Flow

### Direct Completion
User: "تسک چشم‌پزشکی تموم شد"
→ Find task by "چشم‌پزشکی" → ask confirmation → mark as done

### Indirect Completion
User: "چشمم خوب شد" (My eye is better)
→ LLM understands this implies the eye doctor task is done
→ Find task → confirm → mark as done

### What happens on completion:
```python
async def complete_task(user_id: str, task_id: str):
    await db.tasks.update_one(
        {"user_id": user_id, "task_id": task_id},
        {
            "$set": {
                "status": "done",
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        }
    )
    # Cancel any pending reminders for this task
    await db.jobs.update_many(
        {"task_id": task_id, "status": "pending"},
        {"$set": {"status": "cancelled"}}
    )
    # If recurring, create next occurrence
    task = await db.get_task(user_id, task_id)
    if task.recurrence.enabled:
        await create_next_occurrence(task)
```

---

## Task Deletion Flow

**Always requires explicit confirmation.**

```
User: تسک خرید کفش رو پاک کن
Bot:  مطمئنی میخوای این تسکو پاک کنی؟
      📝 خرید کفش (اولویت: ۴)
      بگو "آره" یا "نه"
User: آره
Bot:  ✅ تسک حذف شد
```

### Soft Delete vs Hard Delete
We use **soft delete** — set `status: "cancelled"` instead of actually removing the document. This allows:
- Undo within 24 hours
- Analytics on task patterns
- Recovery from mistakes

---

## Task Query Flow

### Query Types

| User Says | Query Type | Filter |
|-----------|-----------|--------|
| "امروز چیکار دارم؟" | Today's tasks | `due_date = today`, `status = pending` |
| "فردا چیکار دارم؟" | Tomorrow's tasks | `due_date = tomorrow`, `status = pending` |
| "این هفته چیکار دارم؟" | This week's tasks | `due_date in [today...sunday]`, `status = pending` |
| "لیست تسک‌ها" | All pending | `status = pending` |
| "تسک‌های انجام شده" | Completed | `status = done` |
| "تسک‌های کاری" | By category | `category = work`, `status = pending` |
| "مهم‌ترین کارام" | By priority | `status = pending`, sort by priority ASC |
| "همه تسک‌ها" | Everything | No status filter |

### Query Result Formatting

**For 1-3 tasks — Detailed view:**
```
📋 تسک‌های امروز (۲ تسک):

🔴 ۱. جلسه پروژه جدید
   📅 امروز ساعت ۱۰ | ⏱ ۱ ساعت | 🏷 کار

🟡 ۲. رفتن به چشم‌پزشکی
   📅 امروز ساعت ۳ | ⏱ ۲ ساعت | 🏷 سلامت
```

**For 4+ tasks — Compact view:**
```
📋 تسک‌های این هفته (۶ تسک):

🔴 جلسه پروژه جدید — امروز
🟠 ارائه گزارش — فردا
🟡 چشم‌پزشکی — فردا
🟡 خرید هفتگی — پنجشنبه
🟢 کتاب خوندن — جمعه
⚪ مرتب کردن اتاق — شنبه
```

**For 0 tasks:**
```
🎉 هیچ تسکی نداری! وقت استراحته
```

---

## Category System

### Predefined Categories

| Category | Persian | Description | Priority Bias |
|----------|---------|-------------|---------------|
| `health` | سلامت | Medical, exercise, wellness | +1 (higher) |
| `work` | کار | Job, meetings, deadlines | +0 |
| `family` | خانواده | Family visits, obligations | +0 |
| `learning` | یادگیری | Study, courses, reading | -1 (lower) |
| `personal` | شخصی | Errands, shopping, misc | +0 |
| `other` | سایر | Anything that doesn't fit | +0 |

### Category Inference

The LLM infers category from context:
- "دکتر", "بیمارستان", "دارو", "ورزش" → `health`
- "جلسه", "پروژه", "دفتر", "مدیر" → `work`
- "مامان", "بابا", "خواهر", "مهمونی خانوادگی" → `family`
- "کتاب", "دوره", "یاد بگیرم", "تمرین" → `learning`

If ambiguous (e.g., "جلسه خانوادگی"), the LLM picks the most likely or asks.

### Custom Categories
Users can create custom categories. If the LLM sees a category it doesn't recognize, it either:
- Maps it to the closest predefined category
- Creates a new category for the user (stored in user config)

---

## Error Handling & Edge Cases

### User sends nonsense
```
User: asdfghjkl
Bot:  متوجه نشدم 🤔 یه تسک جدید داری؟ یا میخوای تسک‌هاتو ببینی؟
```

### User says "yes" or "no" when not in confirmation state
```
User: آره
Bot:  (state = idle, nothing to confirm)
Bot:  آره چی؟ 😄 بگو چیکار کنم
```

### User sends too many messages too fast (rate limiting)
```
Bot:  یکم آروم‌تر! ⏳ لطفا ۱۰ ثانیه صبر کن بعد پیام بده
```

### Task limit reached
```
Bot:  به حداکثر تعداد تسک (۲۰۰ تا) رسیدی! بعضی تسک‌های قدیمی رو حذف کن یا تکمیل کن.
```

### MongoDB connection lost
```
Bot:  یه مشکل فنی پیش اومده 🔧 لطفا چند لحظه دیگه دوباره امتحان کن
```
