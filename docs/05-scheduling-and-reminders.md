# 05 - Scheduling, Reminders & Recurring Tasks

## Overview

The scheduling system handles three types of time-based events:

1. **Reminders** — User-requested notifications ("فردا بهم بگو...")
2. **Due-date alerts** — Automatic notifications before a task is due
3. **Recurring tasks** — Tasks that repeat on a schedule

All three share the same underlying scheduler infrastructure but have different trigger logic.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   APScheduler                             │
│              (with MongoDB JobStore)                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Reminder    │  │  Due-Date    │  │  Recurrence   │  │
│  │  Jobs        │  │  Alert Jobs  │  │  Jobs         │  │
│  │              │  │              │  │               │  │
│  │  One-shot    │  │  One-shot    │  │  Cron-like    │  │
│  │  at specific │  │  30min before│  │  triggers     │  │
│  │  time        │  │  due_date    │  │               │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                 │                  │           │
│         └─────────────────┼──────────────────┘           │
│                           │                              │
│                           ▼                              │
│                  ┌─────────────────┐                     │
│                  │  Job Executor   │                     │
│                  │  (sends Telegram│                     │
│                  │   messages)     │                     │
│                  └─────────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

---

## Reminder System

### How Reminders Are Created

**Explicit reminder request:**
```
User: فردا ساعت ۹ بهم بگو از فرزانه بپرسم کدوم کفش رو بگیرم
Bot:  ✅ یادآوری تنظیم شد — فردا ساعت ۹ صبح بهت میگم
```

**Automatic reminder on task creation:**
When a task has a `due_date`, we automatically create a reminder:
- For tasks due tomorrow or later: remind at 9 AM on the due date
- For tasks due today: remind 1 hour before (if time is set), or don't remind
- User can customize default reminder time in config

### Reminder Data Model

```python
class Reminder(BaseModel):
    """A scheduled reminder."""
    job_id: str  # UUID, also used as APScheduler job ID
    user_id: str
    task_id: str | None  # Linked task, or None for standalone reminders
    remind_at: datetime  # When to send
    message: str  # What to say
    status: str  # pending | fired | cancelled
    created_at: datetime
```

### Reminder Execution Flow

```python
async def fire_reminder(job_id: str):
    """Called by APScheduler when a reminder triggers."""

    # 1. Load job from DB
    job = await db.get_job(job_id)
    if not job or job.status != "pending":
        return  # Already fired or cancelled

    # 2. Check quiet hours
    user = await db.get_user(job.user_id)
    if is_quiet_hours(user):
        # Reschedule to end of quiet hours
        new_time = get_quiet_hours_end(user)
        await reschedule_job(job_id, new_time)
        return

    # 3. Send Telegram message
    try:
        await bot.send_message(
            chat_id=job.user_id,
            text=f"🔔 یادآوری: {job.message}"
        )
    except Exception as e:
        logger.error("Failed to send reminder", job_id=job_id, error=str(e))
        # Retry in 5 minutes
        await reschedule_job(job_id, datetime.utcnow() + timedelta(minutes=5))
        return

    # 4. Mark as fired
    await db.mark_job_fired(job_id)

    # 5. If linked to a task, check if task needs attention
    if job.task_id:
        task = await db.get_task(job.user_id, job.task_id)
        if task and task.status == "pending":
            await bot.send_message(
                chat_id=job.user_id,
                text=format_task_reminder(task)
            )
```

### Reminder Message Formatting

**Standalone reminder (no task):**
```
🔔 یادآوری: از فرزانه بپرس کدوم کفش رو بگیری
```

**Task-linked reminder:**
```
🔔 یادآوری تسک:

📝 جلسه پروژه جدید
📅 امروز ساعت ۱۰
🏷 کار | 🔴 اولویت ۱

آماده‌ای؟
```

---

## Due-Date Alert System

### Automatic Alert Rules

| Condition | Alert Time | Message |
|-----------|-----------|---------|
| Task due in > 24 hours | 9 AM on due date | "امروز باید ... انجام بدی" |
| Task due in 1-24 hours | 1 hour before | "یک ساعت دیگه ..." |
| Task overdue | 9 AM next day | "⚠️ این تسک دیروز باید انجام می‌شد: ..." |
| Task due today, no time set | 9 AM | "امروز باید ..." |

### Due-Date Alert Creation

```python
async def schedule_due_date_alerts(task: Task):
    """Create due-date alert jobs for a task."""

    if not task.due_date:
        return

    user = await db.get_user(task.user_id)
    tz = pytz.timezone(user.timezone)
    due_local = task.due_date.astimezone(tz)

    # Morning reminder on due date
    morning_reminder = due_local.replace(hour=9, minute=0, second=0)
    if morning_reminder > datetime.now(tz):
        await create_scheduled_job(
            user_id=task.user_id,
            task_id=task.task_id,
            job_type="due_date_alert",
            trigger_at=morning_reminder,
            message=f"امروز باید انجام بدی: {task.title}",
        )

    # 1 hour before (if specific time is set)
    if task.due_date.hour != 0:  # Has specific time
        one_hour_before = task.due_date - timedelta(hours=1)
        if one_hour_before > datetime.utcnow():
            await create_scheduled_job(
                user_id=task.user_id,
                task_id=task.task_id,
                job_type="due_date_alert",
                trigger_at=one_hour_before,
                message=f"⏰ یک ساعت دیگه: {task.title}",
            )
```

### Overdue Task Checker

A periodic job (runs every hour) checks for overdue tasks:

```python
async def check_overdue_tasks():
    """Periodic job: find overdue tasks and notify users."""

    overdue_tasks = await db.tasks.find({
        "status": "pending",
        "due_date": {"$lt": datetime.utcnow()},
        "due_date": {"$gt": datetime.utcnow() - timedelta(days=7)},  # Only recent overdue
    }).to_list()

    for task in overdue_tasks:
        # Don't spam — check if we already notified today
        already_notified = await db.jobs.find_one({
            "task_id": task["task_id"],
            "job_type": "overdue_alert",
            "status": "fired",
            "created_at": {"$gt": datetime.utcnow() - timedelta(hours=24)},
        })

        if not already_notified:
            await bot.send_message(
                chat_id=task["user_id"],
                text=f"⚠️ این تسک باید انجام می‌شد:\n\n📝 {task['title']}\n📅 {format_date(task['due_date'])}\n\nانجام دادی؟ (آره / نه)",
            )
            await db.create_job(ScheduledJob(
                user_id=task["user_id"],
                task_id=task["task_id"],
                job_type="overdue_alert",
                status="fired",
                trigger_at=datetime.utcnow(),
                message="overdue notification sent",
            ))
```

---

## Recurring Tasks

### How Users Create Recurring Tasks

**Via natural language:**
```
User: هر روز ساعت ۷ صبح ورزش کنم
Bot:  ✅ تسک تکراری اضافه شد — هر روز ساعت ۷ صبح

User: هر هفته شنبه‌ها خرید هفتگی
Bot:  ✅ تسک تکراری اضافه شد — هر شنبه

User: اول هر ماه گزارش بده
Bot:  ✅ تسک تکراری اضافه شد — اول هر ماه
```

### Recurrence Patterns

| Pattern | Cron Expression | Example |
|---------|----------------|---------|
| `daily` | `0 7 * * *` | هر روز ساعت ۷ |
| `weekly` | `0 9 * * 6` | هر شنبه ساعت ۹ |
| `monthly` | `0 9 1 * *` | اول هر ماه ساعت ۹ |
| `weekdays` | `0 9 * * 1-5` | روزهای کاری ساعت ۹ |
| `custom` | User-defined | هر ۳ روز، هر ۲ هفته، ... |

### Recurrence Data Model

```python
class RecurrenceConfig(BaseModel):
    enabled: bool = False
    pattern: str | None = None           # "daily", "weekly", "monthly", etc.
    cron_expression: str | None = None   # For complex patterns
    day_of_week: int | None = None       # 0=Mon, 6=Sun (for weekly)
    day_of_month: int | None = None      # 1-31 (for monthly)
    time_of_day: str | None = None       # "07:00" (when to create/remind)
    next_occurrence: datetime | None = None
    end_date: datetime | None = None     # Optional end date
```

### How Recurring Tasks Work

Recurring tasks are NOT duplicated upfront. Instead:

1. **One "template" task exists** with `recurrence.enabled = True`
2. **A scheduler job** fires at `recurrence.next_occurrence`
3. **When the job fires:**
   - Send a reminder to the user
   - Calculate and set the next occurrence
   - If the user marks it as done, the template stays (for next recurrence)
   - If the user deletes it, the recurrence stops

```python
async def handle_recurring_trigger(task_id: str):
    """Called when a recurring task's next occurrence is reached."""

    task = await db.get_task_by_id(task_id)
    if not task or not task.recurrence.enabled:
        return

    user = await db.get_user(task.user_id)

    # 1. Send reminder
    await bot.send_message(
        chat_id=task.user_id,
        text=f"🔄 تسک تکراری:\n\n📝 {task.title}\n🏷 {task.category}\n\nوقتشه!",
    )

    # 2. Reset task status if it was completed
    if task.status == "done":
        await db.update_task(task.user_id, task.task_id, {
            "status": "pending",
            "completed_at": None,
            "updated_at": datetime.utcnow(),
        })

    # 3. Calculate next occurrence
    next_time = calculate_next_occurrence(task.recurrence)

    if task.recurrence.end_date and next_time > task.recurrence.end_date:
        # Recurrence has ended
        await db.update_task(task.user_id, task.task_id, {
            "recurrence.enabled": False,
            "recurrence.next_occurrence": None,
        })
        await bot.send_message(
            chat_id=task.user_id,
            text=f"✅ تسک تکراری «{task.title}» تمام شد (تاریخ پایان رسید)",
        )
        return

    # 4. Update next occurrence
    await db.update_task(task.user_id, task.task_id, {
        "recurrence.next_occurrence": next_time,
        "due_date": next_time,
    })

    # 5. Schedule next trigger
    await schedule_recurring_job(task, next_time)
```

### Next Occurrence Calculator

```python
from croniter import croniter

def calculate_next_occurrence(recurrence: RecurrenceConfig) -> datetime:
    """Calculate when this recurring task should trigger next."""

    now = datetime.utcnow()

    if recurrence.cron_expression:
        cron = croniter(recurrence.cron_expression, now)
        return cron.get_next(datetime)

    match recurrence.pattern:
        case "daily":
            return now + timedelta(days=1)
        case "weekly":
            # Next occurrence of the same weekday
            days_ahead = recurrence.day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_date = now + timedelta(days=days_ahead)
            return next_date.replace(
                hour=int(recurrence.time_of_day.split(":")[0]),
                minute=int(recurrence.time_of_day.split(":")[1]),
            )
        case "monthly":
            # Next month, same day
            if now.month == 12:
                return now.replace(year=now.year + 1, month=1, day=recurrence.day_of_month)
            return now.replace(month=now.month + 1, day=recurrence.day_of_month)
        case _:
            return now + timedelta(days=1)  # Fallback
```

---

## Scheduler Infrastructure

### APScheduler Setup

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore

class SchedulerService:
    """Manages all scheduled jobs."""

    def __init__(self, mongo_uri: str, db_name: str, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(
            jobstores={
                "default": MongoDBJobStore(
                    database=db_name,
                    collection="apscheduler_jobs",
                    client=AsyncIOMotorClient(mongo_uri),
                )
            },
            job_defaults={
                "coalesce": True,        # If multiple missed fires, run once
                "max_instances": 1,       # Don't run same job concurrently
                "misfire_grace_time": 3600,  # Allow 1 hour late execution
            },
        )

    async def start(self):
        """Start the scheduler. Call once on bot startup."""
        self.scheduler.start()
        # Register the periodic overdue checker
        self.scheduler.add_job(
            check_overdue_tasks,
            trigger="interval",
            hours=1,
            id="overdue_checker",
            replace_existing=True,
        )

    async def schedule_reminder(self, user_id: str, task_id: str | None,
                                 remind_at: datetime, message: str) -> str:
        """Schedule a one-shot reminder."""
        job_id = str(uuid.uuid4())
        self.scheduler.add_job(
            fire_reminder,
            trigger="date",
            run_date=remind_at,
            args=[job_id],
            id=job_id,
        )
        # Also store in our jobs collection for tracking
        await db.create_job(ScheduledJob(
            job_id=job_id,
            user_id=user_id,
            task_id=task_id,
            job_type="reminder",
            trigger_at=remind_at,
            message=message,
            status="pending",
        ))
        return job_id

    async def schedule_recurring(self, task: Task) -> str:
        """Schedule a recurring task trigger."""
        job_id = f"recurring_{task.task_id}"

        if task.recurrence.cron_expression:
            trigger = CronTrigger.from_crontab(task.recurrence.cron_expression)
        else:
            trigger = DateTrigger(run_date=task.recurrence.next_occurrence)

        self.scheduler.add_job(
            handle_recurring_trigger,
            trigger=trigger,
            args=[task.task_id],
            id=job_id,
            replace_existing=True,
        )
        return job_id

    async def cancel_job(self, job_id: str):
        """Cancel a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
        except JobLookupError:
            pass  # Already removed
        await db.mark_job_cancelled(job_id)
```

---

## Quiet Hours

### How It Works

Users can set quiet hours (e.g., 11 PM to 7 AM). During quiet hours:
- **Reminders are deferred** — rescheduled to the end of quiet hours
- **Overdue alerts are deferred** — same
- **The bot still responds** if the user sends a message (they're awake!)

### Configuration

```python
# User config
{
    "quiet_hours": {
        "enabled": true,
        "start": "23:00",  # 11 PM
        "end": "07:00"     # 7 AM
    }
}
```

### Quiet Hours Check

```python
def is_quiet_hours(user: User) -> bool:
    """Check if it's currently quiet hours for this user."""
    if not user.quiet_hours.enabled:
        return False

    tz = pytz.timezone(user.timezone)
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M")

    start = user.quiet_hours.start
    end = user.quiet_hours.end

    if start <= end:
        # Normal range (e.g., 08:00 to 17:00)
        return start <= current_time <= end
    else:
        # Overnight range (e.g., 23:00 to 07:00)
        return current_time >= start or current_time <= end
```

---

## Timezone Handling

### Rules
1. All dates in MongoDB are stored as **UTC**
2. All user-facing dates are displayed in **user's timezone** (default: `Asia/Tehran`)
3. When the LLM resolves "فردا" (tomorrow), it uses the user's timezone to determine what "tomorrow" means
4. APScheduler jobs use UTC internally

### Date Resolution with Timezone

```python
async def resolve_date_for_user(user_id: str, raw_date: str) -> datetime:
    """Resolve a relative date expression in the user's timezone, return UTC."""
    user = await db.get_user(user_id)
    tz = pytz.timezone(user.timezone)
    now_local = datetime.now(tz)

    # Resolve relative to local time
    resolved_local = date_resolver.resolve(raw_date, reference_date=now_local)

    # Convert to UTC for storage
    return resolved_local.astimezone(pytz.UTC)
```

---

## Summary: What Gets Scheduled When

| Event | When Scheduled | Trigger Time | One-shot or Recurring |
|-------|---------------|-------------|----------------------|
| Task reminder | Task created with due_date | 9 AM on due date | One-shot |
| Pre-task alert | Task has specific time | 1 hour before | One-shot |
| User-requested reminder | User says "بهم یادآوری کن" | User-specified time | One-shot |
| Recurring task | Task created with recurrence | Per cron/interval | Recurring |
| Overdue checker | Bot startup | Every 1 hour | Recurring (system) |
| Daily summary (optional) | User enables in config | Every day 8 AM | Recurring (system) |
