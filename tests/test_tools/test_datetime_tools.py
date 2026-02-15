"""Tests for get_current_datetime tool."""
from unittest.mock import AsyncMock

import pytest

from src.tools import datetime_tools


@pytest.mark.asyncio
async def test_get_current_datetime_returns_iso_and_jalali(mock_db):
    """Tool must return iso datetime and jalali date for user timezone."""
    user = await mock_db.get_or_create_user("u1")
    result = await datetime_tools.get_current_datetime("u1", mock_db)
    assert "iso" in result
    assert "jalali_date" in result or "jalali" in result
    assert "timezone" in result or "gregorian_date" in result


@pytest.mark.asyncio
async def test_get_current_datetime_uses_user_timezone(mock_db):
    """Result must reflect user's timezone."""
    await mock_db.get_or_create_user("u1")
    await mock_db.update_user_config("u1", "timezone", "UTC")
    result = await datetime_tools.get_current_datetime("u1", mock_db)
    assert "UTC" in str(result.get("timezone", ""))


@pytest.mark.asyncio
async def test_get_current_datetime_weekday_present(mock_db):
    """Response should include weekday (for Persian or Gregorian)."""
    await mock_db.get_or_create_user("u1")
    result = await datetime_tools.get_current_datetime("u1", mock_db)
    assert "weekday" in result or "jalali_weekday" in result
