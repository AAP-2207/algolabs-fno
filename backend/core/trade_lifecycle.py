"""
backend/core/trade_lifecycle.py

Pure decision logic for the DOS automatic paper-trade lifecycle: when to
enter a trade, and when to exit one. Deliberately kept free of any
database/HTTP calls so it's cheap and reliable to unit test every
scenario — the actual Supabase read/write happens in routers/dos.py,
which calls into these functions.

DESIGN NOTE (documented honestly for the one-pager): entry/exit are fully
automatic, matching how real paper-trading engines behave (e.g. Tradetron,
Streak) — the system decides based on live conditions, a human doesn't
manually confirm each trade. Given the 10-day project scope, this check
runs as a side effect of GET /api/dos/signal being polled by the frontend
every few seconds during active hours, rather than a dedicated background
scheduler — a documented simplification, not a production pattern.

ASSUMPTION CALLED OUT: the spec's "Trailing SL triggers when price closes
above the ST value of the short CE or PE, whichever is lower" is worded
ambiguously. This implementation interprets it as: the trailing SL
triggers when the underlying SuperTrend direction flips away from the
direction that justified entering the trade (exposed as "just_flipped" in
core/supertrend.py's get_current_signal). This is a reasonable, defensible
reading, but it's an interpretation — call this out explicitly if asked.
"""

from datetime import datetime, time
from typing import Literal, Optional, TypedDict

OptionSide = Literal["CE", "PE"]
DayType = Literal["wednesday", "thursday"]
ExitReason = Literal["initial_sl", "trailing_sl", "market_close"]

MARKET_CLOSE_TIME = time(15, 30)  # NSE market close, 3:30 PM IST

BANKNIFTY_LOT_SIZE = 30  # NSE Bank Nifty lot size as of January 2026 revision (reduced from 35 to 30)

# Per spec: initial SL is 50% of premium sold on Wednesday, 100% on Thursday
INITIAL_SL_MULTIPLIER = {
    "wednesday": 1.5,   # premium can rise 50% before initial SL hits
    "thursday": 2.0,    # premium can rise 100% (double) before initial SL hits
}


class OpenTrade(TypedDict):
    strike: int
    option_side: OptionSide
    entry_premium: float
    entry_time: str  # ISO timestamp
    day_type: DayType


def get_day_type(now: datetime) -> Optional[DayType]:
    """Wednesday=2, Thursday=3 in Python's weekday(). Returns None for any
    other day, since a trade should never be entered outside Wed/Thu."""
    weekday = now.weekday()
    if weekday == 2:
        return "wednesday"
    if weekday == 3:
        return "thursday"
    return None


def should_enter_trade(
    is_dos_active: bool,
    has_open_trade_today: bool,
) -> bool:
    """
    Entry condition: DOS must be active (Wed/Thu, post-9:20 AM) AND no
    trade has already been entered today. This enforces the one-trade-
    per-day, one-open-trade-at-a-time rule that also governs the
    backtester, so live and backtest logic stay consistent.
    """
    return is_dos_active and not has_open_trade_today


def compute_initial_sl_price(entry_premium: float, day_type: DayType) -> float:
    """
    Initial SL price level: the premium level at which the initial SL
    triggers. E.g. entry_premium=150, day_type="wednesday" -> SL at 225
    (150 * 1.5, i.e. a 50% rise in premium against a short position).
    """
    multiplier = INITIAL_SL_MULTIPLIER[day_type]
    return entry_premium * multiplier


def check_trailing_sl(current_underlying_close: float, st_ce_value: float, st_pe_value: float) -> tuple[bool, float]:
    """
    Spec rule: Trailing SL triggers when price closes above the ST value of the short CE or PE, whichever is lower.
    Returns (is_triggered, lower_st_level).
    """
    lower_st = min(st_ce_value, st_pe_value)
    return current_underlying_close > lower_st, lower_st


def check_exit_condition(
    open_trade: OpenTrade,
    current_premium: float,
    trend_just_flipped_against_position: bool = False,
    now: Optional[datetime] = None,
    current_underlying_close: Optional[float] = None,
    st_ce_value: Optional[float] = None,
    st_pe_value: Optional[float] = None,
) -> tuple[bool, Optional[ExitReason]]:
    """
    Returns (should_exit, reason). Checks conditions in the order the
    spec implies priority: initial SL first (hard risk limit), then
    trailing SL (closes above min(st_ce, st_pe) or trend flip), then
    default market-close exit.
    """
    initial_sl_price = compute_initial_sl_price(
        open_trade["entry_premium"], open_trade["day_type"]
    )

    if current_premium >= initial_sl_price:
        return True, "initial_sl"

    if current_underlying_close is not None and st_ce_value is not None and st_pe_value is not None:
        trailing_hit, _ = check_trailing_sl(current_underlying_close, st_ce_value, st_pe_value)
        if trailing_hit:
            return True, "trailing_sl"
    elif trend_just_flipped_against_position:
        return True, "trailing_sl"

    if now and now.time() >= MARKET_CLOSE_TIME:
        return True, "market_close"

    return False, None



def compute_pnl(
    entry_premium: float,
    exit_premium: float,
    quantity: int,
) -> float:
    """
    P&L for a SHORT (sold) option position: profit when premium falls,
    loss when premium rises, since the seller collected entry_premium
    and must pay exit_premium to close out (or it's automatically
    settled at exit_premium).
    """
    return (entry_premium - exit_premium) * quantity
