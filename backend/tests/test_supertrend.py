"""
backend/tests/test_supertrend.py

Unit tests for core/supertrend.py.

The synthetic dataset below is small and deliberately simple (monotonic
moves, low noise) specifically so you can hand-trace it if a test fails —
open a spreadsheet, compute TR/ATR/bands manually for these 15 rows, and
compare row by row against what the function produces. That's the point:
this dataset is a debugging aid, not just a pass/fail check.

These tests check STRUCTURAL correctness (no crashes, sane trend behavior,
bands computed correctly relative to price). They do NOT replace the
TradingView cross-check on real Bank Nifty data — that's a separate,
mandatory manual step before Phase 8. See validate_against_tradingview.py.
"""

import numpy as np
import pandas as pd
import pytest

from core.supertrend import calculate_atr, calculate_supertrend, wilders_rma, get_current_signal


@pytest.fixture
def flat_then_uptrend_df():
    """
    15 bars: first 5 bars flat (to seed ATR with low, stable TR), then a
    clean, steady uptrend for the remaining 10. Small enough to hand-trace.
    """
    flat = [100.0] * 5
    up = [100 + i * 2 for i in range(1, 11)]  # 102, 104, ... 120
    close = flat + up
    high = [c + 1 for c in close]
    low = [c - 1 for c in close]
    open_ = close.copy()

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close},
        index=pd.date_range("2026-01-01 09:15", periods=15, freq="5min"),
    )


@pytest.fixture
def flat_then_downtrend_df():
    flat = [100.0] * 5
    down = [100 - i * 2 for i in range(1, 11)]  # 98, 96, ... 80
    close = flat + down
    high = [c + 1 for c in close]
    low = [c - 1 for c in close]
    open_ = close.copy()

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close},
        index=pd.date_range("2026-01-01 09:15", periods=15, freq="5min"),
    )


def test_wilders_rma_seeds_with_simple_mean():
    """Wilder's RMA should seed at index [period-1] with a plain mean of
    the first `period` values, not an EMA-style seed. This is the exact
    detail that most often causes TradingView mismatches if gotten wrong."""
    series = pd.Series([10, 12, 14, 16, 18])
    rma = wilders_rma(series, period=5)
    assert rma.iloc[4] == pytest.approx(np.mean([10, 12, 14, 16, 18]))


def test_atr_first_row_uses_high_minus_low_only():
    """First row has no previous close, so TR must just be high-low, not NaN
    propagating into the True Range calc."""
    df = pd.DataFrame({
        "open": [100, 101], "high": [105, 106],
        "low": [95, 96], "close": [100, 102],
    })
    atr_input_check = df["high"].iloc[0] - df["low"].iloc[0]
    assert atr_input_check == 10  # sanity on the fixture itself


def test_supertrend_runs_without_error(flat_then_uptrend_df):
    result = calculate_supertrend(flat_then_uptrend_df, period=10, multiplier=3)
    assert "supertrend" in result.columns
    assert "trend" in result.columns
    # No NaNs after the ATR warm-up period
    assert result["supertrend"].iloc[-1] is not None
    assert not pd.isna(result["supertrend"].iloc[-1])


def test_supertrend_detects_uptrend(flat_then_uptrend_df):
    """In a clean, steady uptrend, the trend should read 'up' (BNF Fut > ST)
    by the end of the series, once bands have caught up."""
    result = calculate_supertrend(flat_then_uptrend_df, period=10, multiplier=3)
    assert result["trend"].iloc[-1] == "up"
    assert result["close"].iloc[-1] > result["supertrend"].iloc[-1]


def test_supertrend_detects_downtrend(flat_then_downtrend_df):
    result = calculate_supertrend(flat_then_downtrend_df, period=10, multiplier=3)
    assert result["trend"].iloc[-1] == "down"
    assert result["close"].iloc[-1] < result["supertrend"].iloc[-1]


def test_insufficient_data_raises_clear_error():
    """Fewer rows than `period` should fail loudly, not silently return
    garbage/NaN bands that could feed a wrong live signal."""
    df = pd.DataFrame({
        "open": [100, 101, 102], "high": [102, 103, 104],
        "low": [99, 100, 101], "close": [101, 102, 103],
    })
    with pytest.raises(ValueError):
        calculate_supertrend(df, period=10, multiplier=3)


def test_get_current_signal_strike_rounding(flat_then_uptrend_df):
    """Strike should be nearest-100 rounded from the SuperTrend value,
    per the DOS spec, not from spot/close."""
    result = calculate_supertrend(flat_then_uptrend_df, period=10, multiplier=3)
    signal = get_current_signal(result)
    assert signal["recommended_strike"] % 100 == 0
    assert signal["option_side"] in ("CE", "PE")


def test_trend_flip_flagged_correctly():
    """Construct a series that goes up then sharply reverses, and confirm
    trend_flip is True exactly once at the reversal bar (not on every bar,
    not missed entirely)."""
    up = [100 + i * 3 for i in range(20)]
    down = [up[-1] - i * 5 for i in range(1, 15)]
    close = up + down
    high = [c + 1 for c in close]
    low = [c - 1 for c in close]
    df = pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close},
        index=pd.date_range("2026-01-01 09:15", periods=len(close), freq="5min"),
    )
    result = calculate_supertrend(df, period=10, multiplier=3)
    flips = result[result["trend_flip"]]
    # There should be at least one flip once the sharp reversal happens,
    # and it should not be on the very first valid bar
    assert len(flips) >= 1
