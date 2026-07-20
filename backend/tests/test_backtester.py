"""
backend/tests/test_backtester.py

Tests the backtest replay logic using mocked data sources (no live
network calls) — fetch_daily_banknifty_history and get_banknifty_options
are monkeypatched so we can construct exact, hand-verifiable scenarios.
"""

from datetime import date, timedelta

import pandas as pd
import pytest

import core.backtester as backtester_module
from core.backtester import run_single_day_backtest, run_backtest, BacktestTrade


def _synthetic_candles(end_date: date, trend_up: bool, n_days: int = 30) -> pd.DataFrame:
    """Build a clean, steady-trend daily candle series ending exactly at
    end_date, guaranteed to produce a stable, unambiguous SuperTrend
    direction by the final day."""
    dates = pd.date_range(end=end_date, periods=n_days, freq="B")  # business days
    if trend_up:
        close = [45000 + i * 60 for i in range(n_days)]
    else:
        close = [50000 - i * 60 for i in range(n_days)]
    high = [c + 100 for c in close]
    low = [c - 100 for c in close]
    open_ = close.copy()
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=dates)


def _synthetic_options_df(strike: float, option_type: str, open_p: float, high_p: float, close_p: float) -> pd.DataFrame:
    return pd.DataFrame([{
        "TradDt": pd.Timestamp.now(), "TckrSymb": "BANKNIFTY", "XpryDt": pd.Timestamp.now(),
        "StrkPric": strike, "OptnTp": option_type,
        "OpnPric": open_p, "HghPric": high_p, "LwPric": open_p - 20, "ClsPric": close_p,
        "SttlmPric": 0, "OpnIntrst": 1000, "TtlTradgVol": 500,
    }])


def test_non_wed_thu_date_returns_error(monkeypatch):
    monday = date(2026, 7, 13)
    trade = run_single_day_backtest(monday)
    assert trade.error is not None
    assert "Wednesday or Thursday" in trade.error


def test_successful_backtest_market_close_exit(monkeypatch):
    """Uptrend day, premium stays well below SL all day -> market_close exit."""
    wednesday = date(2026, 7, 15)  # confirmed Wednesday

    monkeypatch.setattr(
        backtester_module, "fetch_daily_banknifty_history",
        lambda end_date, lookback_days=60: _synthetic_candles(end_date, trend_up=True),
    )
    monkeypatch.setattr(
        backtester_module, "get_banknifty_options",
        lambda trade_date, expiry_date=None: _synthetic_options_df(
            strike=46100, option_type="CE", open_p=150.0, high_p=180.0, close_p=120.0,
        ),
    )

    trade = run_single_day_backtest(wednesday)
    assert trade.error is None
    assert trade.day_type == "wednesday"
    assert trade.option_side == "CE"  # uptrend -> sell CE
    assert trade.entry_price == 150.0
    assert trade.exit_reason == "market_close"
    assert trade.exit_price == 120.0
    # Short position, premium fell 150->120 -> profit
    assert trade.pnl > 0


def test_initial_sl_hit_wednesday(monkeypatch):
    """Wednesday: initial SL = entry * 1.5. High breaches it -> initial_sl exit."""
    wednesday = date(2026, 7, 15)

    monkeypatch.setattr(
        backtester_module, "fetch_daily_banknifty_history",
        lambda end_date, lookback_days=60: _synthetic_candles(end_date, trend_up=True),
    )
    # entry=150, SL level = 150*1.5 = 225. High of 230 breaches it.
    monkeypatch.setattr(
        backtester_module, "get_banknifty_options",
        lambda trade_date, expiry_date=None: _synthetic_options_df(
            strike=46100, option_type="CE", open_p=150.0, high_p=230.0, close_p=140.0,
        ),
    )

    trade = run_single_day_backtest(wednesday)
    assert trade.error is None
    assert trade.exit_reason == "initial_sl"
    assert trade.exit_price == pytest.approx(225.0)  # exits AT the SL level, not the high
    assert trade.pnl < 0  # SL hit on a short = loss


def test_initial_sl_thursday_is_double_multiplier(monkeypatch):
    """Thursday: initial SL = entry * 2.0 (not 1.5 like Wednesday)."""
    thursday = date(2026, 7, 16)  # confirmed Thursday

    monkeypatch.setattr(
        backtester_module, "fetch_daily_banknifty_history",
        lambda end_date, lookback_days=60: _synthetic_candles(end_date, trend_up=True),
    )
    # entry=100, Wed SL would be 150, Thu SL is 200. High of 180 should NOT breach Thursday's SL.
    monkeypatch.setattr(
        backtester_module, "get_banknifty_options",
        lambda trade_date, expiry_date=None: _synthetic_options_df(
            strike=46100, option_type="CE", open_p=100.0, high_p=180.0, close_p=90.0,
        ),
    )

    trade = run_single_day_backtest(thursday)
    assert trade.error is None
    assert trade.day_type == "thursday"
    assert trade.exit_reason == "market_close"  # 180 < 200 (Thursday SL), so no SL hit


def test_zero_open_price_falls_back_to_close(monkeypatch):
    """Illiquid deep-OTM contracts often show OpnPric=0 — entry should
    fall back to ClsPric rather than using a nonsensical zero entry price."""
    wednesday = date(2026, 7, 15)

    monkeypatch.setattr(
        backtester_module, "fetch_daily_banknifty_history",
        lambda end_date, lookback_days=60: _synthetic_candles(end_date, trend_up=True),
    )
    monkeypatch.setattr(
        backtester_module, "get_banknifty_options",
        lambda trade_date, expiry_date=None: _synthetic_options_df(
            strike=46100, option_type="CE", open_p=0.0, high_p=0.0, close_p=45.0,
        ),
    )

    trade = run_single_day_backtest(wednesday)
    assert trade.error is None
    assert trade.entry_price == 45.0  # fell back to close, not 0


def test_missing_strike_returns_error_not_crash(monkeypatch):
    wednesday = date(2026, 7, 15)

    monkeypatch.setattr(
        backtester_module, "fetch_daily_banknifty_history",
        lambda end_date, lookback_days=60: _synthetic_candles(end_date, trend_up=True),
    )
    # Options data exists but at a totally different strike than SuperTrend recommends
    monkeypatch.setattr(
        backtester_module, "get_banknifty_options",
        lambda trade_date, expiry_date=None: _synthetic_options_df(
            strike=99999, option_type="CE", open_p=50.0, high_p=60.0, close_p=45.0,
        ),
    )

    trade = run_single_day_backtest(wednesday)
    assert trade.error is not None
    assert "No" in trade.error and "contract" in trade.error


def test_run_backtest_aggregates_multiple_days(monkeypatch):
    """Full multi-day backtest: mix of wins, an SL hit, and one failure,
    confirm the summary stats are computed correctly and failures are
    reported separately rather than silently dropped or crashing the batch."""
    call_count = {"n": 0}

    def fake_candles(end_date, lookback_days=60):
        return _synthetic_candles(end_date, trend_up=True)

    def fake_options(trade_date, expiry_date=None):
        call_count["n"] += 1
        if call_count["n"] == 2:
            # Second call: simulate a Bhavcopy failure for this day
            from services.bhavcopy import BhavcopyFetchError
            raise BhavcopyFetchError("simulated fetch failure")
        elif call_count["n"] == 3:
            # Third call: SL hit
            return _synthetic_options_df(strike=46100, option_type="CE", open_p=100, high_p=200, close_p=90)
        else:
            # Wins (market close, premium dropped)
            return _synthetic_options_df(strike=46100, option_type="CE", open_p=150, high_p=160, close_p=100)

    monkeypatch.setattr(backtester_module, "fetch_daily_banknifty_history", fake_candles)
    monkeypatch.setattr(backtester_module, "get_banknifty_options", fake_options)

    dates = [date(2026, 7, 15), date(2026, 7, 16), date(2026, 7, 22)]  # Wed, Thu, Wed
    summary = run_backtest(dates)

    assert summary["total_trades_attempted"] == 3
    assert summary["successful_trades"] == 2
    assert summary["failed_trades"] == 1
    assert len(summary["errors"]) == 1
    assert summary["initial_sl_hit_rate_pct"] == 50.0  # 1 of 2 successful trades hit SL
    assert len(summary["equity_curve"]) == 2


def test_uses_previous_day_trend_not_same_day(monkeypatch):
    """Regression test for the look-ahead bias fix: builds a candle series
    where the trend flips FROM down TO up on trade_date itself. If the
    code incorrectly used trade_date's own row, it would see 'up' (CE).
    Using the correct previous-day row, it must see 'down' (PE) instead,
    since that's what was known at market open before trade_date's own
    price action happened."""
    wednesday = date(2026, 7, 15)

    # Build a candle series: bearish for the first ~25 days, then a sharp
    # reversal starting exactly ON trade_date, strong enough to flip
    # SuperTrend's direction by trade_date's own close.
    dates = pd.date_range(end=wednesday, periods=30, freq="B")
    close = [50000 - i * 80 for i in range(29)] + [50000 - 28 * 80 + 800]  # sharp reversal on the last (trade) day
    high = [c + 100 for c in close]
    low = [c - 100 for c in close]
    open_ = close.copy()
    candles = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=dates)

    monkeypatch.setattr(backtester_module, "fetch_daily_banknifty_history", lambda end_date, lookback_days=60: candles)

    # Capture what strike/side gets requested from get_banknifty_options so we can assert on it
    captured = {}

    def fake_options(trade_date, expiry_date=None):
        captured["called"] = True
        # Serve both PE and CE at both 47200 and 48400 — the exact strike the
        # backtester asks for depends on whichever day's SuperTrend it reads.
        # Previous-day ST lands near 48360 → rounds to 48400.
        # Trade-date ST (look-ahead) would be lower due to the drop → ~47200.
        # By serving both, the trade completes either way and we can assert
        # purely on option_side to detect which row was used.
        rows = []
        for strike in (47200, 48400):
            for side in ("PE", "CE"):
                rows.append({
                    "TradDt": pd.Timestamp.now(), "TckrSymb": "BANKNIFTY", "XpryDt": pd.Timestamp.now(),
                    "StrkPric": strike, "OptnTp": side,
                    "OpnPric": 100.0, "HghPric": 120.0, "LwPric": 80.0, "ClsPric": 90.0,
                    "SttlmPric": 0, "OpnIntrst": 1000, "TtlTradgVol": 500,
                })
        return pd.DataFrame(rows)

    monkeypatch.setattr(backtester_module, "get_banknifty_options", fake_options)

    trade = run_single_day_backtest(wednesday)

    assert trade.error is None
    # THE ACTUAL REGRESSION CHECK: must be PE (bearish, matching the PREVIOUS
    # day's still-intact downtrend), NOT CE (which is what trade_date's own
    # reversed candle would incorrectly suggest if look-ahead bias existed)
    assert trade.option_side == "PE", (
        f"Expected PE (previous day's trend, before the reversal) but got "
        f"{trade.option_side} — this suggests the look-ahead bias fix has "
        f"regressed and is using trade_date's own (future-leaking) candle again."
    )
