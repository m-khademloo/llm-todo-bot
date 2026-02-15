"""ask_user (pause/resume ReAct loop)."""
from typing import Any


async def ask_user(
    user_id: str,
    question: str,
    context: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Ask the user a question and stop. Next message will be the answer."""
    return {
        "waiting_for_response": True,
        "question": question,
        "context": context,
    }
