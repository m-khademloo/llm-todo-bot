"""get_user_config, update_user_config."""
from typing import Any


async def get_user_config(user_id: str, db: Any, **kwargs: Any) -> dict[str, Any]:
    """Get user's preferences."""
    user = await db.get_or_create_user(user_id)
    return {
        "language": user.language,
        "timezone": user.timezone,
        "priority_prompt": user.priority_prompt,
        "default_category": user.default_category,
        "notification_enabled": user.notification_enabled,
        "quiet_hours": {
            "enabled": user.quiet_hours.enabled,
            "start": user.quiet_hours.start,
            "end": user.quiet_hours.end,
        },
    }


async def update_user_config(
    user_id: str, db: Any, key: str, value: Any, **kwargs: Any
) -> dict[str, Any]:
    """Update a user setting."""
    await db.get_or_create_user(user_id)
    ok = await db.update_user_config(user_id, key, value)
    return {"success": ok, "updated_key": key, "new_value": value}
