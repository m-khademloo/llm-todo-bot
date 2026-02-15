"""Tests for tool registry: all tools defined, params, side_effects."""
import pytest

from src.orchestrator.tool_registry import TOOL_REGISTRY


def test_registry_has_get_current_datetime():
    assert "get_current_datetime" in TOOL_REGISTRY
    t = TOOL_REGISTRY["get_current_datetime"]
    assert "description" in t
    assert t["side_effects"] is False


def test_registry_has_get_user_tasks():
    assert "get_user_tasks" in TOOL_REGISTRY
    t = TOOL_REGISTRY["get_user_tasks"]
    assert "parameters" in t
    assert t["side_effects"] is False


def test_registry_has_create_task():
    assert "create_task" in TOOL_REGISTRY
    assert TOOL_REGISTRY["create_task"]["side_effects"] is True


def test_registry_has_update_task():
    assert "update_task" in TOOL_REGISTRY
    assert "task_id" in str(TOOL_REGISTRY["update_task"]["parameters"])


def test_registry_has_complete_task():
    assert "complete_task" in TOOL_REGISTRY


def test_registry_has_request_task_deletion():
    assert "request_task_deletion" in TOOL_REGISTRY or "delete_task" in TOOL_REGISTRY


def test_registry_has_calculate_priority():
    assert "calculate_priority" in TOOL_REGISTRY
    assert TOOL_REGISTRY["calculate_priority"]["side_effects"] is False


def test_registry_has_get_user_config():
    assert "get_user_config" in TOOL_REGISTRY


def test_registry_has_update_user_config():
    assert "update_user_config" in TOOL_REGISTRY


def test_registry_has_set_reminder():
    assert "set_reminder" in TOOL_REGISTRY
    assert TOOL_REGISTRY["set_reminder"]["side_effects"] is True


def test_registry_has_ask_user():
    assert "ask_user" in TOOL_REGISTRY
    assert TOOL_REGISTRY["ask_user"]["side_effects"] is True
    assert "question" in str(TOOL_REGISTRY["ask_user"]["parameters"])


def test_every_entry_has_description_and_side_effects():
    for name, entry in TOOL_REGISTRY.items():
        assert "description" in entry, f"{name} missing description"
        assert "side_effects" in entry, f"{name} missing side_effects"
        assert isinstance(entry["side_effects"], bool), f"{name} side_effects must be bool"
