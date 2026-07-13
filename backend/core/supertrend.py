"""
core/supertrend.py

SuperTrend indicator implementation, built to match TradingView's built-in
SuperTrend indicator exactly (period=10, multiplier=3 per the DOS spec).

CRITICAL DETAIL: TradingView's SuperTrend uses Wilder's smoothing (RMA) for
ATR, NOT a simple rolling mean. This is the single most common reason a
from-scratch SuperTrend implementation fails to match TradingView — using
pandas' plain `.rolling().mean()` on True Range gives a different ATR series
than Wilder's RMA, which then cascades into different bands and different
flip points. This implementation uses Wilder's RMA deliberately.

Expected input: a DataFrame with columns ['open', 'high', 'low', 'close'],
indexed by time, sorted ascending (oldest first).
"""

import pandas as pd
import numpy as np


def wilders_rma(series: pd.Series, period: int) -> pd.Series:
    """
    Wilder's smoothing (RMA). This is what TradingView uses internally for
    ATR in its built-in SuperTrend, and is NOT the same as a simple moving
    average. Formula: RMA[i] = (RMA[i-1] * (period - 1) + value[i]) / period,
    seeded with a simple mean of the first `period` values.
    """
    rma = pd.Series(index=series.index, dtype=float)
    if len(series) < period:
        return rma  # not enough data yet

    # Seed with simple average of the first `period` values
    rma.iloc[period - 1] = series.iloc[:period].mean()

    for i in range(period, len(series)):
        rma.iloc[i] = (rma.iloc[i - 1] * (period - 1) + series.iloc[i]) / period

    return rma


def calculate_atr(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """
    True Range then Wilder's RMA over `period`.
    TR[i] = max(high[i]-low[i], |high[i]-close[i-1]|, |low[i]-close[i-1]|)
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # First row has no prev_close, so its TR is just high-low
    true_range.iloc[0] = tr1.iloc[0]

    atr = wilders_rma(true_range, period)
    return atr


def calculate_supertrend(
    df: pd.DataFrame, period: int = 10, multiplier: float = 3.0
) -> pd.DataFrame:
    """
    Returns a copy of df with added columns:
      - atr
      - basic_upper, basic_lower
      - final_upper, final_lower
      - supertrend       (the ST line value at each bar)
      - trend            ("up" or "down") — "up" means close > supertrend,
                          i.e. price is above the line (bullish / BNF Fut > ST)
      - trend_flip       (True on the bar where trend direction just changed)

    Trend/signal mapping to the DOS spec:
      trend == "up"   -> BNF Fut > ST -> sell CE
      trend == "down" -> BNF Fut < ST -> sell PE
    """
    df = df.copy()
    hl2 = (df["high"] + df["low"]) / 2

    df["atr"] = calculate_atr(df, period)
    df["basic_upper"] = hl2 + multiplier * df["atr"]
    df["basic_lower"] = hl2 - multiplier * df["atr"]

    final_upper = pd.Series(index=df.index, dtype=float)
    final_lower = pd.Series(index=df.index, dtype=float)
    supertrend = pd.Series(index=df.index, dtype=float)
    trend = pd.Series(index=df.index, dtype=object)

    close = df["close"]
    basic_upper = df["basic_upper"]
    basic_lower = df["basic_lower"]

    first_valid = df["atr"].first_valid_index()
    if first_valid is None:
        raise ValueError(
            f"Not enough candles to compute ATR with period={period}. "
            f"Need at least {period + 1} rows, got {len(df)}."
        )

    start_pos = df.index.get_loc(first_valid)

    # Initialize at the first bar where ATR is available
    final_upper.iloc[start_pos] = basic_upper.iloc[start_pos]
    final_lower.iloc[start_pos] = basic_lower.iloc[start_pos]
    # Seed trend: up if price closes below upper band distance is smaller,
    # standard convention is to start in an uptrend if close > basic_lower
    supertrend.iloc[start_pos] = final_lower.iloc[start_pos]
    trend.iloc[start_pos] = "up"

    for i in range(start_pos + 1, len(df)):
        prev_i = i - 1

        # Final upper band
        if (basic_upper.iloc[i] < final_upper.iloc[prev_i]) or (
            close.iloc[prev_i] > final_upper.iloc[prev_i]
        ):
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[prev_i]

        # Final lower band
        if (basic_lower.iloc[i] > final_lower.iloc[prev_i]) or (
            close.iloc[prev_i] < final_lower.iloc[prev_i]
        ):
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[prev_i]

        # SuperTrend value + trend direction
        prev_st = supertrend.iloc[prev_i]
        if prev_st == final_upper.iloc[prev_i]:
            if close.iloc[i] <= final_upper.iloc[i]:
                supertrend.iloc[i] = final_upper.iloc[i]
                trend.iloc[i] = "down"
            else:
                supertrend.iloc[i] = final_lower.iloc[i]
                trend.iloc[i] = "up"
        else:  # prev_st == final_lower.iloc[prev_i]
            if close.iloc[i] >= final_lower.iloc[i]:
                supertrend.iloc[i] = final_lower.iloc[i]
                trend.iloc[i] = "up"
            else:
                supertrend.iloc[i] = final_upper.iloc[i]
                trend.iloc[i] = "down"

    df["final_upper"] = final_upper
    df["final_lower"] = final_lower
    df["supertrend"] = supertrend
    df["trend"] = trend

    # IMPORTANT: rows before `start_pos` have no trend yet (ATR still warming
    # up) — trend is NaN there, not a real "down". A naive `!=` comparison
    # treats NaN != NaN as True, which falsely flags every warm-up row as a
    # "flip". We explicitly require both the current AND previous trend to
    # be real values before counting something as a flip.
    df["trend_flip"] = False
    shifted_trend = df["trend"].shift(1)
    valid_flip_mask = df["trend"].notna() & shifted_trend.notna() & (df["trend"] != shifted_trend)
    df.loc[valid_flip_mask, "trend_flip"] = True

    return df


def get_current_signal(df_with_supertrend: pd.DataFrame) -> dict:
    """
    Given a DataFrame already processed by calculate_supertrend, return the
    latest signal state for the live DOS panel.
    """
    last = df_with_supertrend.iloc[-1]
    direction = last["trend"]
    st_value = last["supertrend"]
    close = last["close"]

    # Strike = nearest 100 rounded from current ST value, per spec
    recommended_strike = round(st_value / 100) * 100

    return {
        "timestamp": str(df_with_supertrend.index[-1]),
        "close": float(close),
        "supertrend_value": float(st_value),
        "trend": direction,  # "up" -> sell CE, "down" -> sell PE
        "option_side": "CE" if direction == "up" else "PE",
        "recommended_strike": int(recommended_strike),
        "just_flipped": bool(last["trend_flip"]),
    }
