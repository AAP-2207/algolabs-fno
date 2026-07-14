"""
backend/tests/test_trade_lifecycle.py
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from core.trade_lifecycle import (
    get_day_type,
    should_enter_trade,
    compute_initial_sl_price,
    check_exit_condition,
    compute_pnl,
)

IST = ZoneInfo("Asia/Kolkata")


def test_get_day_type_wednesday():
    dt = datetime(2026, 7, 15, 10, 0, tzinfo=IST)  # confirmed Wednesday
    assert get_day_type(dt) == "wednesday"


def test_get_day_type_thursday():
    dt = datetime(2026, 7, 16, 10, 0, tzinfo=IST)  # confirmed Thursday
    assert get_day_type(dt) == "thursday"


def test_get_day_type_other_days_returns_none():
    monday = datetime(2026, 7, 13, 10, 0, tzinfo=IST)
    friday = datetime(2026, 7, 17, 10, 0, tzinfo=IST)
    assert get_day_type(monday) is None
    assert get_day_type(friday) is None


def test_should_enter_trade_when_active_and_no_open_trade():
    assert should_enter_trade(is_dos_active=True, has_open_trade_today=False) is True


def test_should_not_enter_trade_when_already_open_today():
    """One trade per day rule — even if active, don't double-enter."""
    assert should_enter_trade(is_dos_active=True, has_open_trade_today=True) is False


def test_should_not_enter_trade_when_inactive():
    assert should_enter_trade(is_dos_active=False, has_open_trade_today=False) is False


def test_initial_sl_wednesday_is_50_percent_rise():
    sl = compute_initial_sl_price(entry_premium=150.0, day_type="wednesday")
    assert sl == pytest.approx(225.0)


def test_initial_sl_thursday_is_100_percent_rise():
    sl = compute_initial_sl_price(entry_premium=150.0, day_type="thursday")
    assert sl == pytest.approx(300.0)


def test_exit_on_initial_sl_hit():
    trade = {
        "strike": 57500, "option_side": "CE", "entry_premium": 150.0,
        "entry_time": "2026-07-15T10:00:00+05:30", "day_type": "wednesday",
    }
    now = datetime(2026, 7, 15, 11, 0, tzinfo=IST)
    should_exit, reason = check_exit_condition(
        trade, current_premium=230.0,  # above 225 SL level
        trend_just_flipped_against_position=False, now=now,
    )
    assert should_exit is True
    assert reason == "initial_sl"


def test_no_exit_when_premium_below_sl_and_no_flip_and_market_open():
    trade = {
        "strike": 57500, "option_side": "CE", "entry_premium": 150.0,
        "entry_time": "2026-07-15T10:00:00+05:30", "day_type": "wednesday",
    }
    now = datetime(2026, 7, 15, 11, 0, tzinfo=IST)
    should_exit, reason = check_exit_condition(
        trade, current_premium=180.0,  # below 225 SL level
        trend_just_flipped_against_position=False, now=now,
    )
    assert should_exit is False
    assert reason is None


def test_exit_on_trailing_sl_trend_flip():
    trade = {
        "strike": 57500, "option_side": "CE", "entry_premium": 150.0,
        "entry_time": "2026-07-15T10:00:00+05:30", "day_type": "wednesday",
    }
    now = datetime(2026, 7, 15, 11, 0, tzinfo=IST)
    should_exit, reason = check_exit_condition(
        trade, current_premium=160.0,  # well below initial SL
        trend_just_flipped_against_position=True, now=now,
    )
    assert should_exit is True
    assert reason == "trailing_sl"


def test_initial_sl_checked_before_trailing_sl():
    """If both conditions are true simultaneously, initial SL (the hard
    risk limit) should be reported as the reason, per the priority order
    documented in check_exit_condition."""
    trade = {
        "strike": 57500, "option_side": "CE", "entry_premium": 150.0,
        "entry_time": "2026-07-15T10:00:00+05:30", "day_type": "wednesday",
    }
    now = datetime(2026, 7, 15, 11, 0, tzinfo=IST)
    should_exit, reason = check_exit_condition(
        trade, current_premium=230.0,  # breaches initial SL
        trend_just_flipped_against_position=True,  # AND trend flipped
        now=now,
    )
    assert should_exit is True
    assert reason == "initial_sl"


def test_exit_on_market_close():
    trade = {
        "strike": 57500, "option_side": "CE", "entry_premium": 150.0,
        "entry_time": "2026-07-15T10:00:00+05:30", "day_type": "wednesday",
    }
    now = datetime(2026, 7, 15, 15, 30, tzinfo=IST)  # exactly market close
    should_exit, reason = check_exit_condition(
        trade, current_premium=160.0, trend_just_flipped_against_position=False, now=now,
    )
    assert should_exit is True
    assert reason == "market_close"


def test_no_exit_just_before_market_close():
    trade = {
        "strike": 57500, "option_side": "CE", "entry_premium": 150.0,
        "entry_time": "2026-07-15T10:00:00+05:30", "day_type": "wednesday",
    }
    now = datetime(2026, 7, 15, 15, 29, tzinfo=IST)
    should_exit, reason = check_exit_condition(
        trade, current_premium=160.0, trend_just_flipped_against_position=False, now=now,
    )
    assert should_exit is False


def test_compute_pnl_profit_when_premium_drops():
    """Short position: entry 150, exit 100 -> seller keeps the difference."""
    pnl = compute_pnl(entry_premium=150.0, exit_premium=100.0, quantity=30)
    assert pnl == pytest.approx((150.0 - 100.0) * 30)
    assert pnl > 0


def test_compute_pnl_loss_when_premium_rises():
    pnl = compute_pnl(entry_premium=150.0, exit_premium=220.0, quantity=30)
    assert pnl == pytest.approx((150.0 - 220.0) * 30)
    assert pnl < 0
