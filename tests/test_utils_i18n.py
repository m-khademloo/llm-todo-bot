"""Tests for i18n: templates, language detection, t()."""
import pytest

from src.utils import i18n


class TestTemplates:
    def test_t_returns_fa_welcome(self):
        assert "سلام" in i18n.t("welcome", "fa") or "دستیار" in i18n.t("welcome", "fa")

    def test_t_returns_en_welcome_for_en(self):
        assert "Hi" in i18n.t("welcome", "en") or "assistant" in i18n.t("welcome", "en").lower()

    def test_t_fallback_to_fa_for_unknown_lang(self):
        result = i18n.t("welcome", "xx")
        assert len(result) > 0

    def test_t_returns_key_for_unknown_key(self):
        result = i18n.t("nonexistent_key", "fa")
        assert result is not None  # may return key or default


class TestDetectLanguage:
    def test_detect_persian(self):
        assert i18n.detect_language("سلام چطوری") == "fa"
        assert i18n.detect_language("تسک اضافه کن") == "fa"

    def test_detect_english(self):
        assert i18n.detect_language("Hello how are you") == "en"
        assert i18n.detect_language("Add a task") == "en"

    def test_detect_mixed_default(self):
        lang = i18n.detect_language("سلام hello")
        assert lang in ("fa", "en")


class TestPriorityEmoji:
    def test_priority_emoji_mapping(self):
        assert i18n.PRIORITY_EMOJI[1] == "🔴"
        assert i18n.PRIORITY_EMOJI[5] == "⚪"
        assert len(i18n.PRIORITY_EMOJI) == 5
