"""Main ReAct loop: Planner → Executor → Observer."""
import json
from typing import Any

from src.db.database import Database
from src.llm.client import LLMClient, LLMResponse
from src.orchestrator.tool_executor import ToolExecutor
from src.orchestrator.tool_registry import TOOL_REGISTRY
from src.utils.i18n import t


def _tool_definitions_for_llm() -> list[dict]:
    """Build OpenAI-format tool definitions from TOOL_REGISTRY."""
    out = []
    for name, meta in TOOL_REGISTRY.items():
        params = meta.get("parameters") or {}
        properties = {}
        required = []
        for k, v in params.items():
            if isinstance(v, str) and "|" in v:
                properties[k] = {"type": "string", "description": v}
            elif isinstance(v, str):
                properties[k] = {"type": "string", "description": v}
            else:
                properties[k] = {"type": "string"}
        out.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta.get("description", ""),
                "parameters": {"type": "object", "properties": properties, "required": required},
            },
        })
    return out


class Orchestrator:
    """Runs the ReAct loop. Makes ZERO decisions about meaning — LLM decides."""

    def __init__(self, db: Database, llm: LLMClient, scheduler: Any | None = None):
        self.db = db
        self.llm = llm
        self.scheduler = scheduler
        self.tool_executor = ToolExecutor(db, llm, scheduler)
        self._tool_defs = _tool_definitions_for_llm()
        self._max_iterations = 10

    async def handle_message(self, user_id: str, message: str) -> str:
        """Main entry point. One user message → one bot response."""
        msg_stripped = message.strip()
        if msg_stripped == "/start":
            await self.db.clear_conversation_context(user_id)
            user = await self.db.get_or_create_user(user_id)
            return t("welcome", user.language or "fa")

        saved = await self.db.get_conversation_context(user_id)
        if saved and saved.get("messages"):
            messages = list(saved["messages"])
            messages.append({
                "role": "user",
                "content": message,
            })
        else:
            user = await self.db.get_or_create_user(user_id)
            history = await self.db.get_history(user_id, limit=10)
            system = self._build_system_prompt(user)
            messages = [{"role": "system", "content": system}]
            for h in reversed(history):
                role = h.get("role") or h.get("content", {}).get("role")
                content = h.get("content") if isinstance(h.get("content"), str) else (h.get("content") or {}).get("text", "")
                if role and content and role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": message})

        response = await self._react_loop(user_id, messages)
        await self.db.add_message(user_id, "user", message)
        await self.db.add_message(user_id, "assistant", response)
        return response

    def _build_system_prompt(self, user: Any) -> str:
        base = """You are a personal task management assistant on Telegram.
You help the user manage their tasks through natural conversation.
LANGUAGE: Respond in the same language the user writes in (usually Persian/Farsi).
Use tools to get real information. If you need the date, call get_current_datetime. If you need tasks, call get_user_tasks.
Keep messages SHORT. Use emojis sparingly."""
        if getattr(user, "priority_prompt", None):
            base += f"\nUSER PRIORITY: {user.priority_prompt}"
        return base

    async def _react_loop(self, user_id: str, messages: list[dict]) -> str:
        for _ in range(self._max_iterations):
            llm_response = await self.llm.call_with_tools(
                messages=messages,
                tools=self._tool_defs,
                temperature=0.3,
                max_tokens=2000,
            )
            if not llm_response.tool_calls:
                text = (llm_response.content or "").strip()
                if text:
                    await self.db.clear_conversation_context(user_id)
                    return text
                continue
            tool_calls_list = []
            for tc in llm_response.tool_calls:
                name = tc.function.name if hasattr(tc.function, "name") else tc.function.get("name")
                args_str = tc.function.arguments if hasattr(tc.function, "arguments") else tc.function.get("arguments", "{}")
                tool_calls_list.append((tc, name, args_str))
            messages.append({
                "role": "assistant",
                "content": llm_response.content or "",
                "tool_calls": [{"id": tc.id, "function": {"name": name, "arguments": args_str}} for tc, name, args_str in tool_calls_list],
            })
            for tc, name, args_str in tool_calls_list:
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {}
                args["_user_id"] = user_id
                result = await self.tool_executor.execute(name, args)
                if name == "ask_user" and result.get("waiting_for_response") and result.get("question"):
                    await self.db.save_conversation_context(user_id, messages)
                    return result["question"]
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })
        await self.db.clear_conversation_context(user_id)
        return t("error_generic", "fa")
