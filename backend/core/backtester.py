"""
backend/core/backtester.py

Replays the DOS strategy against historical data, one expiry Wed/Thu at a
time. Reuses the same SuperTrend and trade-lifecycle logic used live.

HONEST SCOPE LIMITATIONS (documented per project convention, not hidden —
mention these explicitly in the README/one-pager):

1. Bhav Copy is END-OF-DAY only — NSE doesn't publish free historical
   intraday option premium data. This backtester therefore operates at
   DAILY granularity, not the 5-minute granularity the live DOS panel
   uses. SuperTrend here is computed on DAILY Bank Nifty candles (via
   yfinance, which retains years of daily history — unlike 5-min data,
   which yfinance only retains ~60 days of).

2. Entry price is approximated as the option's Open price that day, or
   Close if Open is 0/unavailable (common for illiquid deep-OTM contracts
   that had no trade at the opening print).

3. Initial SL detection uses the day's High (HghPric) — if High >= the
   initial SL price level, the SL is marked as hit THAT DAY, with the SL
   price itself used as the exit price. This is the standard convention
   for daily-bar backtests: the exact intrabar fill price isn't knowable
   from EOD data, so a fill at the trigger level is assumed.

4. Trailing SL (which depends on detecting an intraday SuperTrend flip)
   CANNOT be accurately modeled at daily granularity — it requires
   knowing whether the underlying crossed the ST line WITHIN the day.
   This backtester only checks initial SL and market-close exit; trailing
   SL is not simulated here. This is surfaced explicitly in results, not
   silently ignored.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

from core.supertrend import calculate_supertrend
from core.trade_lifecycle import get_day_type, compute_initial_sl_price, compute_pnl, BANKNIFTY_LOT_SIZE
from services.bhavcopy import get_banknifty_options, BhavcopyFetchError


@dataclass
class BacktestTrade:
    trade_date: date
    day_type: str
    option_side: str
    strike: float
    entry_price: float
    exit_price: float
    exit_reason: str  # "initial_sl" or "market_close"
    pnl: float
    supertrend_value: float
    error: Optional[str] = None  # if set, other fields are best-effort/zeroed — check this first


def fetch_daily_banknifty_history(end_date: date, lookback_days: int = 60) -> pd.DataFrame:
    """
    Daily Bank Nifty candles ending at end_date, going back lookback_days
    calendar days — comfortably more than the ~15-20 trading days needed
    for SuperTrend's period=10 warm-up (accounting for weekends/holidays).
    """
    start = end_date - timedelta(days=lookback_days)
    ticker = yf.Ticker("^NSEBANK")
    df = ticker.history(
        start=start.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),
        interval="1d",
    )

    if df.empty:
        raise ValueError(f"yfinance returned no daily Bank Nifty history for {start} to {end_date}")

    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
    df = df[["open", "high", "low", "close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def run_single_day_backtest(trade_date: date) -> BacktestTrade:
    """
    Backtests one single expiry day (must be a Wednesday or Thursday, and
    must fall within the window Bank Nifty weekly options were active:
    May 2016 - Nov 2024). Always check .error before trusting other
    fields — a failure at any step returns a BacktestTrade with error set
    rather than raising, so a full multi-week backtest can report partial
    results instead of crashing on one bad day.
    """
    day_type = get_day_type(trade_date)  # date.weekday() works the same as datetime.weekday()
    if day_type is None:
        return BacktestTrade(
            trade_date=trade_date, day_type="unknown", option_side="", strike=0,
            entry_price=0, exit_price=0, exit_reason="", pnl=0, supertrend_value=0,
            error=f"{trade_date} is not a Wednesday or Thursday — DOS only trades expiry days",
        )

    try:
        candles = fetch_daily_banknifty_history(end_date=trade_date)
        result = calculate_supertrend(candles, period=10, multiplier=3)
    except Exception as e:
        return BacktestTrade(
            trade_date=trade_date, day_type=day_type, option_side="", strike=0,
            entry_price=0, exit_price=0, exit_reason="", pnl=0, supertrend_value=0,
            error=f"SuperTrend computation failed: {e}",
        )

    # Uses the previous day's closed SuperTrend value, not trade_date's own —
    # using trade_date's own candle would leak future information (that day's
    # own High/Low/Close) into a decision that must be made at market open,
    # before that day's price action has happened. This is a look-ahead bias fix.
    result_dates = result.index.date
    prev_day_indices = [i for i, d in enumerate(result_dates) if d < trade_date]
    if not prev_day_indices:
        return BacktestTrade(
            trade_date=trade_date, day_type=day_type, option_side="", strike=0,
            entry_price=0, exit_price=0, exit_reason="", pnl=0, supertrend_value=0,
            error=f"No prior trading day found before {trade_date} in fetched history",
        )

    row = result.iloc[prev_day_indices[-1]]  # last trading day strictly before trade_date
    if pd.isna(row["trend"]):
        return BacktestTrade(
            trade_date=trade_date, day_type=day_type, option_side="", strike=0,
            entry_price=0, exit_price=0, exit_reason="", pnl=0, supertrend_value=0,
            error=f"SuperTrend not yet warmed up on {trade_date} (insufficient prior history)",
        )

    trend = row["trend"]
    supertrend_value = float(row["supertrend"])
    option_side = "CE" if trend == "up" else "PE"
    recommended_strike = round(supertrend_value / 100) * 100

    try:
        options_df = get_banknifty_options(trade_date=trade_date, expiry_date=trade_date)
    except BhavcopyFetchError as e:
        return BacktestTrade(
            trade_date=trade_date, day_type=day_type, option_side=option_side,
            strike=recommended_strike, entry_price=0, exit_price=0, exit_reason="",
            pnl=0, supertrend_value=supertrend_value,
            error=f"Bhavcopy fetch failed: {e}",
        )

    matching = options_df[
        (options_df["StrkPric"] == recommended_strike) & (options_df["OptnTp"] == option_side)
    ]
    if matching.empty:
        available = sorted(options_df[options_df["OptnTp"] == option_side]["StrkPric"].unique())
        return BacktestTrade(
            trade_date=trade_date, day_type=day_type, option_side=option_side,
            strike=recommended_strike, entry_price=0, exit_price=0, exit_reason="",
            pnl=0, supertrend_value=supertrend_value,
            error=f"No {option_side} contract at strike {recommended_strike}. Available: {available}",
        )

    opt_row = matching.iloc[0]
    entry_price = float(opt_row["OpnPric"]) if opt_row["OpnPric"] > 0 else float(opt_row["ClsPric"])
    day_high = float(opt_row["HghPric"]) if opt_row["HghPric"] > 0 else entry_price
    day_close = float(opt_row["ClsPric"])

    initial_sl_price = compute_initial_sl_price(entry_price, day_type)

    if day_high >= initial_sl_price:
        exit_price = initial_sl_price
        exit_reason = "initial_sl"
    else:
        exit_price = day_close
        exit_reason = "market_close"

    pnl = compute_pnl(entry_price, exit_price, BANKNIFTY_LOT_SIZE)

    return BacktestTrade(
        trade_date=trade_date, day_type=day_type, option_side=option_side,
        strike=recommended_strike, entry_price=entry_price, exit_price=exit_price,
        exit_reason=exit_reason, pnl=pnl, supertrend_value=supertrend_value,
        error=None,
    )


def run_backtest(trade_dates: list[date]) -> dict:
    """
    Runs run_single_day_backtest across a list of dates and summarizes
    results. Days that errored are excluded from win-rate/P&L stats but
    listed separately so failures are visible, not silently dropped.
    """
    trades = [run_single_day_backtest(d) for d in trade_dates]

    successful = [t for t in trades if t.error is None]
    failed = [t for t in trades if t.error is not None]

    total_pnl = sum(t.pnl for t in successful)
    wins = [t for t in successful if t.pnl > 0]
    sl_hits = [t for t in successful if t.exit_reason == "initial_sl"]

    equity_curve = []
    running_total = 0.0
    for t in successful:
        running_total += t.pnl
        equity_curve.append({"trade_date": t.trade_date.isoformat(), "cumulative_pnl": running_total})

    return {
        "total_trades_attempted": len(trades),
        "successful_trades": len(successful),
        "failed_trades": len(failed),
        "win_rate_pct": round(100 * len(wins) / len(successful), 1) if successful else None,
        "avg_pnl": round(total_pnl / len(successful), 2) if successful else None,
        "total_pnl": round(total_pnl, 2),
        "initial_sl_hit_rate_pct": round(100 * len(sl_hits) / len(successful), 1) if successful else None,
        "equity_curve": equity_curve,
        "trades": [
            {
                "trade_date": t.trade_date.isoformat(), "day_type": t.day_type,
                "option_side": t.option_side, "strike": t.strike,
                "entry_price": t.entry_price, "exit_price": t.exit_price,
                "exit_reason": t.exit_reason, "pnl": t.pnl,
            }
            for t in successful
        ],
        "errors": [{"trade_date": t.trade_date.isoformat(), "error": t.error} for t in failed],
    }
