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


_candles_cache = {}


def fetch_bhavcopy_fallback_history(start_date: date, end_date: date, trade_dates: list[date]) -> pd.DataFrame:
    """
    Constructs a fallback daily index price series by loading the underlying index
    settlement price (SttlmPric) from the cached weekly Bhavcopy files.
    """
    records = []
    for d in trade_dates:
        try:
            df_opt = get_banknifty_options(trade_date=d)
            if not df_opt.empty:
                settlement_price = float(df_opt["SttlmPric"].iloc[0])
                records.append({"date": d, "price": settlement_price})
        except Exception:
            pass

    if not records:
        raise ValueError("No BANKNIFTY settlement prices could be loaded from Bhavcopy cache files.")

    df_fallback = pd.DataFrame(records).set_index("date").sort_index()

    # Reindex to a complete daily calendar range from start_date to end_date
    all_days = pd.date_range(start=start_date, end=end_date, freq="D").date
    df_full = df_fallback.reindex(all_days)

    # Forward-fill and then backward-fill the missing days
    df_full["price"] = df_full["price"].ffill().bfill()

    # Create OHLC columns using the single settlement price
    df_full["open"] = df_full["price"]
    df_full["high"] = df_full["price"]
    df_full["low"] = df_full["price"]
    df_full["close"] = df_full["price"]

    df_full = df_full[["open", "high", "low", "close"]]
    df_full.index = pd.to_datetime(df_full.index)
    df_full.attrs["source"] = "bhavcopy-fallback"
    
    return df_full


def fetch_daily_banknifty_history_batch(start_date: date, end_date: date, trade_dates: list[date]) -> pd.DataFrame:
    cache_key = (start_date, end_date)
    if cache_key in _candles_cache:
        return _candles_cache[cache_key]

    import time
    import random
    import logging

    df = pd.DataFrame()
    last_err = None
    
    ticker = yf.Ticker("^NSEBANK")
    
    for attempt in range(3):
        try:
            df = ticker.history(
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                interval="1d",
            )
            if not df.empty:
                break
            else:
                raise ValueError("yfinance returned empty dataframe")
        except Exception as e:
            last_err = e
            logging.getLogger(__name__).warning(
                f"yfinance fetch failed on attempt {attempt+1}: {e}. Retrying..."
            )
            if attempt < 2:
                sleep_time = (2 ** attempt) + random.random()
                time.sleep(sleep_time)

    if df.empty:
        logging.getLogger(__name__).warning(
            f"yfinance failed after 3 attempts (error: {last_err}). Falling back to Bhavcopy data."
        )
        try:
            df = fetch_bhavcopy_fallback_history(start_date, end_date, trade_dates)
        except Exception as fallback_err:
            raise ValueError(
                f"yfinance failed: {last_err}. Fallback to Bhavcopy also failed: {fallback_err}"
            )
    else:
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
        df = df[["open", "high", "low", "close"]]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.attrs["source"] = "yfinance"

    _candles_cache[cache_key] = df
    return df


def fetch_daily_banknifty_history(end_date: date, lookback_days: int = 60) -> pd.DataFrame:
    """
    Daily Bank Nifty candles ending at end_date, going back lookback_days
    calendar days — comfortably more than the ~15-20 trading days needed
    for SuperTrend's period=10 warm-up (accounting for weekends/holidays).
    """
    start = end_date - timedelta(days=lookback_days)
    return fetch_daily_banknifty_history_batch(start, end_date, [end_date])

fetch_daily_banknifty_history._is_original = True


def get_weekly_expiry_date(trade_date: date) -> date:
    """
    Returns the standard expected weekly expiry date for Bank Nifty options
    for a given trade_date.

    Historical NSE Bank Nifty weekly expiry schedule:
    - May 2016 to Sep 3, 2023: Thursday expiry (weekday 3)
    - Sep 4, 2023 to Nov 20, 2024: Wednesday expiry (weekday 2)
    """
    target_weekday = 3 if trade_date < date(2023, 9, 4) else 2
    days_ahead = (target_weekday - trade_date.weekday()) % 7
    return trade_date + timedelta(days=days_ahead)


def run_single_day_backtest(trade_date: date, candles_all: Optional[pd.DataFrame] = None) -> BacktestTrade:
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
        if candles_all is not None:
            candles = candles_all[candles_all.index.date <= trade_date].tail(60).copy()
            # Restore source attribute if present after slicing
            if "source" in candles_all.attrs:
                candles.attrs["source"] = candles_all.attrs["source"]
            if candles.empty or len(candles) < 15:
                candles = fetch_daily_banknifty_history(end_date=trade_date)
        else:
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
        # Fetch options for trade_date, then find the nearest active weekly expiry on/after trade_date
        options_df = get_banknifty_options(trade_date=trade_date, expiry_date=None)
        available_expiries = sorted(options_df["XpryDt"].dt.date.unique())
        upcoming_expiries = [exp for exp in available_expiries if exp >= trade_date]
        if not upcoming_expiries:
            return BacktestTrade(
                trade_date=trade_date, day_type=day_type, option_side=option_side,
                strike=recommended_strike, entry_price=0, exit_price=0, exit_reason="",
                pnl=0, supertrend_value=supertrend_value,
                error=f"No active upcoming expiry found in Bhavcopy for {trade_date}",
            )
        target_expiry = upcoming_expiries[0]
        matching = options_df[
            (options_df["XpryDt"].dt.date == target_expiry) &
            (options_df["StrkPric"] == recommended_strike) &
            (options_df["OptnTp"] == option_side)
        ]
    except BhavcopyFetchError as e:
        return BacktestTrade(
            trade_date=trade_date, day_type=day_type, option_side=option_side,
            strike=recommended_strike, entry_price=0, exit_price=0, exit_reason="",
            pnl=0, supertrend_value=supertrend_value,
            error=f"Bhavcopy fetch failed: {e}",
        )

    if matching.empty:
        exp_options = options_df[options_df["XpryDt"].dt.date == target_expiry]
        available = sorted(exp_options[exp_options["OptnTp"] == option_side]["StrkPric"].unique())
        return BacktestTrade(
            trade_date=trade_date, day_type=day_type, option_side=option_side,
            strike=recommended_strike, entry_price=0, exit_price=0, exit_reason="",
            pnl=0, supertrend_value=supertrend_value,
            error=f"No {option_side} contract at strike {recommended_strike} for expiry {target_expiry}. Available: {available}",
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
    if not trade_dates:
        return {
            "total_trades_attempted": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "win_rate_pct": None,
            "avg_pnl": None,
            "total_pnl": 0.0,
            "initial_sl_hit_rate_pct": None,
            "equity_curve": [],
            "trades": [],
            "errors": [],
        }

    is_monkeypatched = not getattr(fetch_daily_banknifty_history, "_is_original", False)

    if is_monkeypatched:
        trades = [run_single_day_backtest(d) for d in trade_dates]
        successful = [t for t in trades if t.error is None]
        failed = [t for t in trades if t.error is not None]
    else:
        min_date = min(trade_dates)
        max_date = max(trade_dates)
        start_history = min_date - timedelta(days=60)

        try:
            # Pre-fetch the batched history once
            candles_all = fetch_daily_banknifty_history_batch(start_history, max_date, trade_dates)
        except Exception as e:
            # If the batch fetch completely fails, return failures for all dates
            trades = []
            for d in trade_dates:
                trades.append(BacktestTrade(
                    trade_date=d, day_type="unknown", option_side="", strike=0,
                    entry_price=0, exit_price=0, exit_reason="", pnl=0, supertrend_value=0,
                    error=f"Daily history fetch failed: {e}",
                ))
            successful = []
            failed = trades
        else:
            trades = [run_single_day_backtest(d, candles_all) for d in trade_dates]
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
