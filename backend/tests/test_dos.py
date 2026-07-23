"""
backend/tests/test_dos.py

Tests for the DOS active/inactive gating logic — the Wed/Thu + 9:20 AM
window. This is worth testing thoroughly on its own because a weekday
off-by-one or timezone slip here would silently show the DOS panel as
active/inactive on the wrong days, and that's the kind of bug that's easy
to miss visually if you only ever check the app on the actual current day.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from routers.dos import is_dos_active, IST

# A known reference week: Mon 2026-07-13 through Sun 2026-07-19
# (matches the actual week used in the SuperTrend TradingView validation)
MONDAY = datetime(2026, 7, 13, 10, 0, tzinfo=IST)
TUESDAY = datetime(2026, 7, 14, 10, 0, tzinfo=IST)
WEDNESDAY = datetime(2026, 7, 15, 10, 0, tzinfo=IST)
THURSDAY = datetime(2026, 7, 16, 10, 0, tzinfo=IST)
FRIDAY = datetime(2026, 7, 17, 10, 0, tzinfo=IST)
SATURDAY = datetime(2026, 7, 18, 10, 0, tzinfo=IST)
SUNDAY = datetime(2026, 7, 19, 10, 0, tzinfo=IST)


@pytest.mark.parametrize("dt,label", [
    (MONDAY, "Monday"),
    (TUESDAY, "Tuesday"),
    (FRIDAY, "Friday"),
    (SATURDAY, "Saturday"),
    (SUNDAY, "Sunday"),
])
def test_inactive_on_non_wed_thu_days(dt, label):
    active, reason = is_dos_active(dt)
    assert active is False
    assert "Wednesday and Thursday" in reason


def test_active_on_wednesday_after_920am():
    dt = WEDNESDAY.replace(hour=9, minute=20)
    active, reason = is_dos_active(dt)
    assert active is True
    assert reason == "active"


def test_active_on_thursday_after_920am():
    dt = THURSDAY.replace(hour=9, minute=20)
    active, reason = is_dos_active(dt)
    assert active is True
    assert reason == "active"


def test_inactive_on_wednesday_before_920am():
    """9:19 AM should still be inactive — boundary check."""
    dt = WEDNESDAY.replace(hour=9, minute=19)
    active, reason = is_dos_active(dt)
    assert active is False
    assert "9:20" in reason


def test_active_exactly_at_920am():
    """Exactly 9:20:00 should count as active (>=, not >)."""
    dt = WEDNESDAY.replace(hour=9, minute=20, second=0)
    active, reason = is_dos_active(dt)
    assert active is True


def test_active_late_in_the_day_wednesday():
    """Should remain active through market close, e.g. 15:25."""
    dt = WEDNESDAY.replace(hour=15, minute=25)
    active, reason = is_dos_active(dt)
    assert active is True


def test_inactive_before_market_open_wednesday():
    """Well before market open, e.g. 6 AM — should be inactive on the time check."""
    dt = WEDNESDAY.replace(hour=6, minute=0)
    active, reason = is_dos_active(dt)
    assert active is False
    assert "9:20" in reason


def test_reason_names_actual_weekday():
    """The inactive reason should name the correct day, not a generic message —
    this makes the frontend banner readable/debuggable."""
    active, reason = is_dos_active(MONDAY)
    assert "Monday" in reason

    active, reason = is_dos_active(FRIDAY)
    assert "Friday" in reason


def test_get_dos_trades_endpoint():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    response = client.get("/api/dos/trades")
    assert response.status_code == 200
    data = response.json()
    assert "trades" in data
    assert "source" in data

