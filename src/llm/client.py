"""LiteLLM wrapper: call_with_tools + call_simple."""
from typing import Any


class LLMResponse:
    """Response from LLM that may contain tool_calls or content."""
    def __init__(self, content: str = "", tool_calls: list[Any] | None = None):
        self.content = content or ""
        self.tool_calls = tool_calls or []


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
        raise NotImplementedError

    async def call_simple(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> str:
        """Simple call without tools (for sub-agents like priority calculator)."""
        raise NotImplementedError
