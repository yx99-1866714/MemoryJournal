"""Tests for the recurring tasks service — period bounds and task generation."""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.recurring_tasks import _period_bounds


class TestPeriodBounds:
    """Unit tests for _period_bounds helper."""

    def test_daily_bounds(self):
        # Wednesday March 18, 2026 at 3pm UTC
        now = datetime(2026, 3, 18, 15, 30, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("daily", now)
        assert start == datetime(2026, 3, 18, 0, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 3, 18, 23, 59, 59, tzinfo=timezone.utc)

    def test_weekly_bounds_midweek(self):
        # Wednesday March 18, 2026
        now = datetime(2026, 3, 18, 10, 0, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("weekly", now)
        # Monday March 16 to Sunday March 22
        assert start.day == 16
        assert start.weekday() == 0  # Monday
        assert end.day == 22
        assert end.weekday() == 6  # Sunday

    def test_weekly_bounds_on_monday(self):
        # Monday March 16, 2026
        now = datetime(2026, 3, 16, 8, 0, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("weekly", now)
        assert start.day == 16
        assert end.day == 22

    def test_weekly_bounds_on_sunday(self):
        # Sunday March 22, 2026
        now = datetime(2026, 3, 22, 20, 0, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("weekly", now)
        assert start.day == 16  # Still the same week's Monday
        assert end.day == 22

    def test_monthly_bounds(self):
        # March 2026
        now = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("monthly", now)
        assert start.day == 1
        assert end.day == 31  # March has 31 days

    def test_monthly_bounds_february(self):
        # February 2026 (non-leap year)
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("monthly", now)
        assert start.day == 1
        assert end.day == 28

    def test_monthly_bounds_february_leap_year(self):
        # February 2028 (leap year)
        now = datetime(2028, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("monthly", now)
        assert start.day == 1
        assert end.day == 29

    def test_yearly_bounds(self):
        now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        start, end = _period_bounds("yearly", now)
        assert start.month == 1 and start.day == 1
        assert end.month == 12 and end.day == 31

    def test_unknown_frequency_raises(self):
        now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Unknown frequency"):
            _period_bounds("biweekly", now)
