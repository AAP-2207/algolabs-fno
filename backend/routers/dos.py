"""
backend/routers/dos.py

GET /api/dos/signal — returns the current DOS strategy signal state.

Gating logic (per spec): DOS is only active on Wednesday and Thursday,
starting at 9:20 AM IST or later. Outside that window, this returns an
explicit inactive state with a reason — the frontend should show this as
an intentional banner, not a blank/broken panel (this matters because an
evaluator may open the DOS screen on any day of the week).
"""

from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from fastapi import APIRouter
from pydantic import BaseModel

from core.supertrend import calculate_supertrend, get_current_signal
from core.backtester import run_backtest, get_weekly_expiry_date
from services.bhavcopy import BhavcopyFetchError
try:
    from .market_data import get_greeks
except ImportError:
    from routers.market_data import get_greeks

import os
from supabase import create_client, Client

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

if supabase_url and (supabase_url.endswith("/rest/v1/") or supabase_url.endswith("/rest/v1")):
    supabase_url = supabase_url.replace("/rest/v1/", "").replace("/rest/v1", "")

supabase_client: Client = None
if supabase_url and supabase_key:
    try:
        supabase_client = create_client(supabase_url, supabase_key)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"DOS Router: Failed to initialize Supabase client: {e}")

router = APIRouter()

IST = ZoneInfo("Asia/Kolkata")
ENTRY_TIME = time(9, 20)  # 9:20 AM per spec — market opens 9:15, first 5 min excluded
# Python's weekday(): Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
DOS_ACTIVE_WEEKDAYS = {2, 3}  # Wednesday, Thursday


def get_ist_now() -> datetime:
    return datetime.now(IST)


def is_dos_active(now: datetime | None = None) -> tuple[bool, str]:
    """
    Returns (is_active, reason_or_status_string).
    Pure function, no I/O — deliberately kept this way so it's cheap and
    reliable to unit test every weekday/time combination without needing
    to mock the clock in complicated ways.
    """
    now = now or get_ist_now()
    weekday = now.weekday()

    if weekday not in DOS_ACTIVE_WEEKDAYS:
        day_name = now.strftime("%A")
        return False, f"DOS strategy is only active on Wednesday and Thursday (today is {day_name})"

    if now.time() < ENTRY_TIME:
        return False, f"DOS strategy activates at 9:20 AM IST (current time: {now.strftime('%H:%M')})"

    return True, "active"


def fetch_recent_bnf_candles(period: str = "5d") -> pd.DataFrame:
    """
    Pull recent Bank Nifty 5-min candles via yfinance (^NSEBANK) — same
    source used in the SuperTrend validation script, unaffected by the
    NSE/Akamai block on the Render backend.

    NOTE: per spec, DOS technically trades Bank Nifty FUTURES, not the
    index. If you have a futures-specific feed wired elsewhere, swap the
    ticker/source here — everything downstream only needs columns
    ['open', 'high', 'low', 'close'], indexed by time.
    """
    ticker = yf.Ticker("^NSEBANK")
    df = ticker.history(period=period, interval="5m")
    if df.empty:
        raise RuntimeError("yfinance returned no Bank Nifty candles")

    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low", "Close": "close",
    })
    df = df[["open", "high", "low", "close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_convert(IST)
    return df


@router.get("/api/dos/signal")
def get_dos_signal(bypass_gating: bool = False):
    now = get_ist_now()
    if bypass_gating:
        active, reason = True, "active"
    else:
        active, reason = is_dos_active(now)

    if not active:
        return {
            "active": False,
            "reason": reason,
            "timestamp": now.isoformat(),
        }

    candles = fetch_recent_bnf_candles()
    result = calculate_supertrend(candles, period=10, multiplier=3)
    signal = get_current_signal(result)

    # ------------------------------------------------------------------
    # INTEGRATION POINT — wire this to your existing option chain service
    # from Phase 4/5. signal["recommended_strike"] and signal["option_side"]
    # (CE/PE) are already computed here. You still need LTP/IV/Greeks for
    # THAT specific strike — reuse whatever function your /api/option-chain
    # or /api/greeks route already calls to fetch+compute a single strike.
    # ------------------------------------------------------------------
    import logging
    logger = logging.getLogger(__name__)

    signal["strike_data_available"] = False
    try:
        greeks_data = get_greeks(symbol="BANKNIFTY")
        strikes = greeks_data.get("strikes", [])

        recommended_strike = signal["recommended_strike"]
        option_side = signal["option_side"]

        strike_data = None
        for item in strikes:
            if abs(item["strike"] - recommended_strike) < 1.0:
                strike_data = item.get(option_side)
                break

        if strike_data:
            signal["ltp"] = strike_data["ltp"]
            signal["iv"] = strike_data.get("computed_iv") or strike_data.get("nse_iv") or 0.0
            signal["delta"] = strike_data["delta"]
            signal["gamma"] = strike_data["gamma"]
            signal["theta"] = strike_data["theta"]
            signal["vega"] = strike_data["vega"]
            signal["strike_data_available"] = True
        else:
            logger.warning(f"DOS signal: no strike data found for strike={recommended_strike} side={option_side}")
            signal["ltp"] = None
            signal["iv"] = None
            signal["delta"] = None
            signal["gamma"] = None
            signal["theta"] = None
            signal["vega"] = None
    except Exception as e:
        logger.error(f"DOS signal: failed to fetch greeks data: {e}")
        signal["ltp"] = None
        signal["iv"] = None
        signal["delta"] = None
        signal["gamma"] = None
        signal["theta"] = None
        signal["vega"] = None

    # Format historical candles for the frontend chart (dropping NaN warm-up rows)
    chart_candles = []
    valid_candles = result.dropna(subset=["supertrend"])
    for timestamp, row in valid_candles.iterrows():
        chart_candles.append({
            "time": timestamp.strftime("%d-%b %H:%M") if hasattr(timestamp, "strftime") else str(timestamp),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "supertrend": float(row["supertrend"]),
            "trend": str(row["trend"]),
        })

    # Initialize open_trade as None
    open_trade_response = None

    if supabase_client is not None:
        try:
            from core.trade_lifecycle import (
                should_enter_trade,
                get_day_type,
                check_exit_condition,
                compute_pnl,
                compute_initial_sl_price,
                BANKNIFTY_LOT_SIZE
            )
            
            today_date = now.date().isoformat()
            # 1. Fetch trades for today (IST)
            response = supabase_client.table("dos_trades") \
                .select("*") \
                .eq("trade_date", today_date) \
                .eq("is_backtest", False) \
                .execute()
            
            trades_today = response.data if (response and response.data) else []
            
            # Find the active open trade if any (where exit_time is null)
            open_trade_row = None
            for t in trades_today:
                if t.get("exit_time") is None:
                    open_trade_row = t
                    break
            
            has_open_trade_today = len(trades_today) > 0
            
            # 2. No open trade today, and we're active
            if open_trade_row is None and active:
                day_type = get_day_type(now)
                if day_type is not None:
                    should_enter = should_enter_trade(
                        is_dos_active=True,
                        has_open_trade_today=has_open_trade_today
                    )
                    if should_enter:
                        entry_premium = signal.get("ltp")
                        if entry_premium is not None:
                            insert_data = {
                                "trade_date": today_date,
                                "day_type": day_type,
                                "option_type": signal["option_side"],
                                "strike": signal["recommended_strike"],
                                "entry_time": now.isoformat(),
                                "entry_premium": float(entry_premium),
                                "is_backtest": False
                            }
                            insert_res = supabase_client.table("dos_trades").insert(insert_data).execute()
                            if insert_res and insert_res.data:
                                open_trade_row = insert_res.data[0]
                        else:
                            logger.warning("DOS Trade Lifecycle: Entry premium is None, skipping entry this cycle.")
            
            # 3. Open trade exists, check exit condition
            elif open_trade_row is not None:
                current_premium = signal.get("ltp")
                if current_premium is not None:
                    trade_to_check = {
                        "strike": int(open_trade_row["strike"]),
                        "option_side": open_trade_row["option_type"],
                        "entry_premium": float(open_trade_row["entry_premium"]),
                        "entry_time": open_trade_row["entry_time"],
                        "day_type": open_trade_row["day_type"],
                    }
                    should_exit, reason = check_exit_condition(
                        open_trade=trade_to_check,
                        current_premium=float(current_premium),
                        trend_just_flipped_against_position=signal["just_flipped"],
                        now=now
                    )
                    if should_exit:
                        pnl_value = compute_pnl(float(open_trade_row["entry_premium"]), float(current_premium), quantity=BANKNIFTY_LOT_SIZE)
                        update_data = {
                            "exit_time": now.isoformat(),
                            "exit_premium": float(current_premium),
                            "exit_reason": reason,
                            "pnl": float(pnl_value)
                        }
                        update_res = supabase_client.table("dos_trades") \
                            .update(update_data) \
                            .eq("id", open_trade_row["id"]) \
                            .execute()
                        open_trade_row = None
                else:
                    logger.debug("DOS Trade Lifecycle: Current premium is None, skipping exit checks this cycle.")

            # 4. Form open_trade object for response
            if open_trade_row is not None:
                entry_premium = float(open_trade_row["entry_premium"])
                current_premium = signal.get("ltp")
                unrealized_pnl = None
                if current_premium is not None:
                    unrealized_pnl = entry_premium - float(current_premium)
                
                initial_sl_price = compute_initial_sl_price(entry_premium, open_trade_row["day_type"])
                
                open_trade_response = {
                    "strike": int(open_trade_row["strike"]),
                    "option_side": open_trade_row["option_type"],
                    "entry_premium": entry_premium,
                    "entry_time": open_trade_row["entry_time"],
                    "day_type": open_trade_row["day_type"],
                    "current_premium": current_premium,
                    "initial_sl_price": initial_sl_price,
                    "unrealized_pnl": unrealized_pnl
                }

        except Exception as e:
            logger.error(f"DOS Trade Lifecycle: DB operation failed: {e}", exc_info=True)
            open_trade_response = None

    # If bypass_gating is on and no real trade was found/set, inject a mock trade for demo purposes
    if bypass_gating and open_trade_response is None:
        from core.trade_lifecycle import compute_initial_sl_price as _compute_sl
        recommended_strike = signal.get("recommended_strike") or 52000
        option_side = signal.get("option_side") or "CE"
        ltp_val = signal.get("ltp") or 120.0
        entry_premium = round(ltp_val * 1.15, 2)
        initial_sl_price = _compute_sl(entry_premium, "wednesday")
        open_trade_response = {
            "strike": int(recommended_strike),
            "option_side": option_side,
            "entry_premium": entry_premium,
            "entry_time": now.isoformat(),
            "day_type": "wednesday",
            "current_premium": ltp_val,
            "initial_sl_price": initial_sl_price,
            "unrealized_pnl": round((entry_premium - ltp_val) * 30, 2)
        }

    response_data = {
        "active": True,
        "timestamp": now.isoformat(),
        "candles": chart_candles,
        "open_trade": open_trade_response,
        **signal,
    }

    if open_trade_response is not None:
        try:
            from core.interpretation import generate_dos_trade_card
            response_data["trade_card_text"] = generate_dos_trade_card({
                "option_side": open_trade_response["option_side"],
                "strike": open_trade_response["strike"],
                "day_type": open_trade_response["day_type"],
                "entry_premium": open_trade_response["entry_premium"],
                "current_premium": open_trade_response.get("current_premium"),
                "is_open": True,
                "exit_reason": None,
            })
        except Exception as e:
            logger.error(f"Failed to generate trade card text: {e}")

    return response_data


# ---------------------------------------------------------------------------
# Backtest endpoint
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    start_date: Optional[str] = "2024-02-07"  # YYYY-MM-DD; our validated known-good window
    weeks: Optional[int] = 4


def _is_last_thursday_of_month(d: date) -> bool:
    return d.weekday() == 3 and (d + timedelta(days=7)).month != d.month


def _generate_expiry_dates(start_date: date, weeks: int) -> list[date]:
    """
    Generates exactly one expiry date per week for the `weeks` consecutive weeks
    starting from start_date. Uses get_weekly_expiry_date for standard weekly
    regimes (Thursday before Sep 2023, Wednesday after) and shifts to Thursday
    for monthly-expiry weeks (last Thursday of the month).
    """
    dates = []
    # Find the standard weekly expiry of the starting date's week
    base_expiry = get_weekly_expiry_date(start_date)

    for i in range(weeks):
        next_base = base_expiry + timedelta(weeks=i)
        if next_base >= date(2023, 9, 4):
            # In the Wednesday weekly expiry regime
            # Check if the Thursday of this week is the last Thursday of the month
            thu_of_week = next_base + timedelta(days=1)
            if _is_last_thursday_of_month(thu_of_week):
                dates.append(thu_of_week)
            else:
                dates.append(next_base)
        else:
            # In the Thursday weekly expiry regime
            dates.append(next_base)

    return dates



@router.post("/api/dos/backtest")
def run_dos_backtest(req: BacktestRequest):
    import logging
    logger = logging.getLogger(__name__)

    try:
        start = date.fromisoformat(req.start_date)
    except (ValueError, TypeError) as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"Invalid start_date '{req.start_date}': {e}")

    dates = _generate_expiry_dates(start, req.weeks)

    # First pass — run with the generated dates as-is
    summary = run_backtest(dates)

    # Calendar-quirk correction: for any date that errored with a missing-expiry
    # Bhavcopy message, retry with date+1 and splice the result in.
    corrected_errors = []
    for err_entry in summary["errors"]:
        err_msg = err_entry.get("error", "")
        failed_date = date.fromisoformat(err_entry["trade_date"])
        # Only retry for missing-data errors, not network failures
        if "No BANKNIFTY rows" in err_msg or "Available expiries" in err_msg:
            retry_date = failed_date + timedelta(days=1)
            
            # Prevent double-counting if retry_date is already in dates or already in summary["trades"]
            already_scheduled_or_traded = (
                retry_date in dates or
                any(t["trade_date"] == retry_date.isoformat() for t in summary["trades"])
            )
            if already_scheduled_or_traded:
                logger.info(
                    f"Backtest: skipping retry of {failed_date} as {retry_date} "
                    f"because {retry_date} is already in backtest schedule/trades"
                )
                corrected_errors.append(err_entry)
                continue

            logger.info(
                f"Backtest: retrying {failed_date} as {retry_date} "
                f"(calendar-quirk correction)"
            )
            retry_summary = run_backtest([retry_date])
            if retry_summary["successful_trades"] > 0:
                # Merge the recovered trade into the main summary
                summary["trades"].extend(retry_summary["trades"])
                summary["successful_trades"] += retry_summary["successful_trades"]
                summary["failed_trades"] -= 1  # no longer a failure
                # Recompute derived stats with the full successful set
                all_pnls = [t["pnl"] for t in summary["trades"]]
                total_pnl = sum(all_pnls)
                wins = [p for p in all_pnls if p > 0]
                sl_hits = [t for t in summary["trades"] if t["exit_reason"] == "initial_sl"]
                n = len(all_pnls)
                summary["total_pnl"] = round(total_pnl, 2)
                summary["avg_pnl"] = round(total_pnl / n, 2) if n else None
                summary["win_rate_pct"] = round(100 * len(wins) / n, 1) if n else None
                summary["initial_sl_hit_rate_pct"] = round(100 * len(sl_hits) / n, 1) if n else None
                # Rebuild equity curve in date order
                all_trades_sorted = sorted(summary["trades"], key=lambda t: t["trade_date"])
                running = 0.0
                summary["equity_curve"] = []
                for t in all_trades_sorted:
                    running += t["pnl"]
                    summary["equity_curve"].append({
                        "trade_date": t["trade_date"],
                        "cumulative_pnl": running,
                    })
            else:
                corrected_errors.append(err_entry)  # retry also failed, keep original error
        else:
            corrected_errors.append(err_entry)


    summary["errors"] = corrected_errors

    # Persist successful trades to Supabase with is_backtest=True
    if supabase_client is not None and summary["trades"]:
        try:
            rows = [
                {
                    "trade_date": t["trade_date"],
                    "day_type": t["day_type"],
                    "option_type": t["option_side"],   # matches live schema column name
                    "strike": t["strike"],
                    "entry_premium": t["entry_price"],
                    "exit_premium": t["exit_price"],
                    "exit_reason": t["exit_reason"],
                    "pnl": t["pnl"],
                    "is_backtest": True,
                }
                for t in summary["trades"]
            ]
            supabase_client.table("dos_trades").insert(rows).execute()
            logger.info(f"Backtest: persisted {len(rows)} trade(s) to dos_trades")
        except Exception as e:
            # Graceful degradation — log but don't fail the response
            logger.warning(f"Backtest: Supabase persistence failed (summary still returned): {e}")

    return summary


@router.get("/api/dos/trades")
def get_dos_trades(limit: int = 50, is_backtest: Optional[bool] = None):
    """Fetch persisted trade log from Supabase `dos_trades` table."""
    if supabase_client is None:
        return {"trades": [], "source": "mock", "count": 0}

    try:
        query = supabase_client.table("dos_trades").select("*").order("created_at", desc=True).limit(limit)
        if is_backtest is not None:
            query = query.eq("is_backtest", is_backtest)

        res = query.execute()
        trades = res.data if res and res.data else []
        return {
            "trades": trades,
            "source": "supabase",
            "count": len(trades)
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error fetching dos_trades: {e}")
        return {"trades": [], "source": "error", "error": str(e), "count": 0}

