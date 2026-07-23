"""
backend/tests/test_expiry_calc.py

Tests the weekly expiry calculation logic for Bank Nifty options across
historical regime changes (Thursday expiries before Sep 2023, Wednesday expiries after).
"""

from datetime import date
from core.backtester import get_weekly_expiry_date


def test_expiry_date_calc_before_sept_2023_thursday_regime():
    # Thursday Aug 10, 2023 -> expires same day (Aug 10, 2023)
    thu_date = date(2023, 8, 10)
    assert get_weekly_expiry_date(thu_date) == date(2023, 8, 10)

    # Tuesday Aug 8, 2023 -> expires upcoming Thursday (Aug 10, 2023)
    tue_date = date(2023, 8, 8)
    assert get_weekly_expiry_date(tue_date) == date(2023, 8, 10)


def test_expiry_date_calc_after_sept_2023_wednesday_regime():
    # Wednesday Jan 3, 2024 -> expires same day (Jan 3, 2024)
    wed_date = date(2024, 1, 3)
    assert get_weekly_expiry_date(wed_date) == date(2024, 1, 3)

    # Thursday Jan 4, 2024 -> expires upcoming Wednesday (Jan 10, 2024)
    thu_date = date(2024, 1, 4)
    assert get_weekly_expiry_date(thu_date) == date(2024, 1, 10)

    # Thursday Feb 8, 2024 -> expires upcoming Wednesday (Feb 14, 2024)
    thu_feb = date(2024, 2, 8)
    assert get_weekly_expiry_date(thu_feb) == date(2024, 2, 14)
