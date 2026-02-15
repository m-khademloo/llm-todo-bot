"""Template strings and language detection."""

TEMPLATES: dict[str, dict[str, str]] = {
    "fa": {
        "welcome": "سلام! 👋 من دستیار مدیریت تسک‌هات هستم. بگو چیکار کنم!",
        "help": "من می‌تونم تسک اضافه کنم، لیست بدم، تکمیل یا حذف کنم. فقط بگو چی میخوای.",
        "error_generic": "یه مشکل فنی پیش اومده 🔧 لطفا دوباره امتحان کن",
        "error_rate_limit": "یکم آروم‌تر! ⏳ لطفا چند ثانیه صبر کن",
        "no_tasks": "🎉 هیچ تسکی نداری! وقت استراحته",
        "task_created": "✅ تسک اضافه شد!",
        "task_deleted": "✅ تسک حذف شد",
        "task_completed": "✅ تسک تکمیل شد",
    },
    "en": {
        "welcome": "Hi! 👋 I'm your task management assistant. Tell me what to do!",
        "help": "I can add tasks, list them, complete or delete. Just say what you want.",
        "error_generic": "Something went wrong 🔧 Please try again",
        "error_rate_limit": "Slow down! ⏳ Please wait a few seconds",
        "no_tasks": "🎉 No tasks! Time to relax",
        "task_created": "✅ Task added!",
        "task_deleted": "✅ Task deleted",
        "task_completed": "✅ Task completed",
    },
}

PRIORITY_EMOJI = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}


def t(key: str, lang: str = "fa") -> str:
    """Get a template string in the user's language."""
    lang_map = TEMPLATES.get(lang, TEMPLATES["fa"])
    return lang_map.get(key, TEMPLATES["fa"].get(key, key))


def detect_language(message: str) -> str:
    """Detect if message is primarily Persian or English."""
    if not message or not message.strip():
        return "fa"
    persian_chars = sum(1 for c in message if "\u0600" <= c <= "\u06FF")
    total_alpha = sum(1 for c in message if c.isalpha())
    if total_alpha == 0:
        return "fa"
    if persian_chars / total_alpha > 0.5:
        return "fa"
    return "en"
