"""Tests for LLM client: call_with_tools, call_simple."""
from unittest.mock import AsyncMock, patch

import pytest

from src.llm.client import LLMClient, LLMResponse


@pytest.mark.asyncio
async def test_llm_client_init():
    client = LLMClient(model="gpt-4o-mini", base_url=None)
    assert client.model == "gpt-4o-mini"
    assert client.base_url is None


@pytest.mark.asyncio
async def test_call_with_tools_returns_llm_response():
    from unittest.mock import AsyncMock
    client = LLMClient(model="openai/gpt-4o-mini", base_url=None)
    with patch("src.llm.client.acompletion", new_callable=AsyncMock) as m:
        m.return_value = type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "Hi", "tool_calls": None})()})()]})()
        out = await client.call_with_tools(messages=[{"role": "user", "content": "Hi"}], tools=[])
        assert isinstance(out, LLMResponse)
        assert out.content == "Hi"


@pytest.mark.asyncio
async def test_call_simple_returns_string():
    from unittest.mock import AsyncMock
    client = LLMClient(model="openai/gpt-4o-mini", base_url=None)
    with patch("src.llm.client.acompletion", new_callable=AsyncMock) as m:
        m.return_value = type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "OK"})()})()]})()
        out = await client.call_simple(messages=[{"role": "user", "content": "Hi"}])
        assert isinstance(out, str)
        assert out == "OK"


def test_llm_response_has_content_and_tool_calls():
    r = LLMResponse(content="Hello", tool_calls=[])
    assert r.content == "Hello"
    assert r.tool_calls == []


def test_llm_response_default_empty_tool_calls():
    r = LLMResponse(content="Hi")
    assert r.tool_calls == []
