"""Tests for get_user_config and update_user_config."""
import pytest

from src.tools import config_tools


@pytest.mark.asyncio
async def test_get_user_config_returns_user_preferences(mock_db, sample_user):
    await mock_db.get_or_create_user(
        sample_user.user_id,
        first_name=sample_user.first_name,
        language=sample_user.language,
        timezone=sample_user.timezone,
    )
    result = await config_tools.get_user_config(sample_user.user_id, mock_db)
    assert "language" in result or "timezone" in result
    assert result.get("language", "fa") == "fa"
    assert result.get("timezone", "Asia/Tehran") == "Asia/Tehran"


@pytest.mark.asyncio
async def test_get_user_config_creates_user_if_missing(mock_db):
    result = await config_tools.get_user_config("new_user", mock_db)
    assert result is not None
    u = await mock_db.get_user("new_user")
    assert u is not None


@pytest.mark.asyncio
async def test_update_user_config_language(mock_db, sample_user):
    await mock_db.get_or_create_user(sample_user.user_id)
    result = await config_tools.update_user_config(
        sample_user.user_id, mock_db, "language", "en"
    )
    assert result.get("success") is True or "updated" in str(result).lower()
    u = await mock_db.get_user(sample_user.user_id)
    assert u.language == "en"


@pytest.mark.asyncio
async def test_update_user_config_timezone(mock_db, sample_user):
    await mock_db.get_or_create_user(sample_user.user_id)
    await config_tools.update_user_config(
        sample_user.user_id, mock_db, "timezone", "UTC"
    )
    u = await mock_db.get_user(sample_user.user_id)
    assert u.timezone == "UTC"


@pytest.mark.asyncio
async def test_update_user_config_priority_prompt(mock_db, sample_user):
    await mock_db.get_or_create_user(sample_user.user_id)
    prompt = "Health > Work > Family"
    await config_tools.update_user_config(
        sample_user.user_id, mock_db, "priority_prompt", prompt
    )
    u = await mock_db.get_user(sample_user.user_id)
    assert u.priority_prompt == prompt


@pytest.mark.asyncio
async def test_update_user_config_quiet_hours(mock_db, sample_user):
    await mock_db.get_or_create_user(sample_user.user_id)
    await config_tools.update_user_config(
        sample_user.user_id,
        mock_db,
        "quiet_hours",
        {"enabled": True, "start": "23:00", "end": "07:00"},
    )
    u = await mock_db.get_user(sample_user.user_id)
    assert u.quiet_hours.enabled is True
