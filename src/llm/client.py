"""LiteLLM wrapper: call_with_tools + call_simple."""
from typing import Any

from litellm import acompletion


class _ToolCall:
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.function = type("Fn", (), {"name": name, "arguments": arguments})()


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
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools,
            "tool_choice": "auto",
        }
        if self.base_url:
            kwargs["api_base"] = self.base_url
        response = await acompletion(**kwargs)
        msg = response.choices[0].message
        tool_calls = []
        raw_tc = getattr(msg, "tool_calls", None) or []
        for tc in raw_tc:
            if isinstance(tc, dict):
                fn = tc.get("function") or {}
                tool_calls.append(_ToolCall(
                    id=tc.get("id", ""),
                    name=fn.get("name", ""),
                    arguments=fn.get("arguments", "{}"),
                ))
            else:
                tool_calls.append(tc)
        content = getattr(msg, "content", None) or ""
        return LLMResponse(content=content, tool_calls=tool_calls)

    async def call_simple(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> str:
        """Simple call without tools (for sub-agents like priority calculator)."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.base_url:
            kwargs["api_base"] = self.base_url
        response = await acompletion(**kwargs)
        msg = response.choices[0].message
        return getattr(msg, "content", None) or ""

