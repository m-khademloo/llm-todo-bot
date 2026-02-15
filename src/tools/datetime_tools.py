"""get_current_datetime tool."""
from datetime import datetime
from typing import Any

import jdatetime
import pytz


async def get_current_datetime(
    user_id: str, db: Any, **kwargs: Any
) -> dict[str, Any]:
    """Get the current date and time in the user's timezone."""
    user = await db.get_or_create_user(user_id)
    tz_name = (user.timezone or "Asia/Tehran").strip()
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    jnow = jdatetime.datetime.fromgregorian(datetime=now)
    weekdays_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    months_fa = [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
    ]
    return {
        "iso": now.isoformat(),
        "timezone": str(tz),
        "jalali_date": f"{jnow.day} {months_fa[jnow.month - 1]} {jnow.year}",
        "jalali_weekday": weekdays_fa[jnow.weekday()],
        "weekday": weekdays_fa[jnow.weekday()],
        "gregorian_date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "unix_timestamp": int(now.timestamp()),
    }
