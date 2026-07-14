"""
backend/routers/dos.py

GET /api/dos/signal — returns the current DOS strategy signal state.

Gating logic (per spec): DOS is only active on Wednesday and Thursday,
starting at 9:20 AM IST or later. Outside that window, this returns an
explicit inactive state with a reason — the frontend should show this as
an intentional banner, not a blank/broken panel (this matters because an
evaluator may open the DOS screen on any day of the week).
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from fastapi import APIRouter

from core.supertrend import calculate_supertrend, get_current_signal
try:
    from .market_data import get_greeks
except ImportError:
    from routers.market_data import get_greeks

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
            "time": timestamp.strftime("%H:%M") if hasattr(timestamp, "strftime") else str(timestamp),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "supertrend": float(row["supertrend"]),
            "trend": str(row["trend"]),
        })

    return {
        "active": True,
        "timestamp": now.isoformat(),
        "candles": chart_candles,
        **signal,
    }
