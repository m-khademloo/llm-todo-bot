"""get_current_datetime tool."""
from typing import Any


async def get_current_datetime(
    user_id: str, db: Any, **kwargs: Any
) -> dict[str, Any]:
    """Get the current date and time in the user's timezone."""
    raise NotImplementedError
