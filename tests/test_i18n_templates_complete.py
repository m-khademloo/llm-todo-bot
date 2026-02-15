"""All i18n template keys exist for fa and en."""
import pytest

from src.utils.i18n import TEMPLATES, PRIORITY_EMOJI, t


def test_fa_has_required_keys():
    required = ["welcome", "help", "error_generic", "error_rate_limit", "no_tasks", "task_created", "task_deleted", "task_completed"]
    for key in required:
        assert key in TEMPLATES["fa"], f"fa missing key: {key}"


def test_en_has_required_keys():
    required = ["welcome", "help", "error_generic", "error_rate_limit", "no_tasks", "task_created", "task_deleted", "task_completed"]
    for key in required:
        assert key in TEMPLATES["en"], f"en missing key: {key}"


def test_t_returns_string_for_every_key():
    for key in TEMPLATES["fa"]:
        assert isinstance(t(key, "fa"), str)
        assert len(t(key, "fa")) > 0


def test_priority_emoji_all_priorities():
    for p in range(1, 6):
        assert p in PRIORITY_EMOJI
        assert len(PRIORITY_EMOJI[p]) > 0
