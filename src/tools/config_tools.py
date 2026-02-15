"""get_user_config, update_user_config."""
from typing import Any


async def get_user_config(user_id: str, db: Any, **kwargs: Any) -> dict[str, Any]:
    """Get user's preferences."""
    raise NotImplementedError


async def update_user_config(
    user_id: str, db: Any, key: str, value: Any, **kwargs: Any
) -> dict[str, Any]:
    """Update a user setting."""
    raise NotImplementedError
