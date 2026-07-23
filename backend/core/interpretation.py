"""
backend/core/interpretation.py

Plain-language interpretation logic for the option chain and DOS strategy,
per the assignment spec's requirement for "plain-language interpretation
cards" (PCR signal, max pain, IV spike commentary) and an auto-generated
DOS trade card.

All functions here are pure (no I/O, no network) — they take already-
fetched option chain / trade data and return numbers or strings. This
keeps them cheap and reliable to unit test, same pattern as core/supertrend.py
and core/trade_lifecycle.py.
"""

from typing import Optional, TypedDict


class StrikeOI(TypedDict):
    strike: float
    call_oi: float
    put_oi: float


# ---------------------------------------------------------------------------
# Put-Call Ratio (PCR)
# ---------------------------------------------------------------------------

def calculate_pcr(strikes: list[StrikeOI]) -> float:
    """
    PCR = Total Put OI / Total Call OI across the option chain.
    Standard, widely-used sentiment indicator. Raises ValueError if total
    call OI is zero (undefined ratio) rather than silently returning inf
    or a misleading number.
    """
    total_call_oi = sum(s["call_oi"] for s in strikes)
    total_put_oi = sum(s["put_oi"] for s in strikes)

    if total_call_oi == 0:
        raise ValueError("Total Call OI is zero — PCR is undefined for this option chain")

    return total_put_oi / total_call_oi


def interpret_pcr(pcr: float) -> str:
    """
    Plain-language PCR interpretation using commonly-cited retail-trading
    heuristic bands (the same convention used by most option-chain
    commentary tools, e.g. PCR > ~1.3 read as heavy put writing / a
    contrarian bullish signal, since put SELLERS are betting the market
    won't fall below that level). This is a heuristic commentary aid, not
    a rigorous quantitative trading signal — worth stating plainly if asked.
    """
    if pcr > 1.3:
        return (
            f"PCR is {pcr:.2f} — notably high. Heavy put writing suggests traders are "
            f"selling puts expecting support to hold; often read as a mildly bullish "
            f"contrarian signal (option WRITERS, not buyers, are positioned this way)."
        )
    elif pcr < 0.7:
        return (
            f"PCR is {pcr:.2f} — notably low. Heavy call writing suggests traders are "
            f"selling calls expecting resistance to hold; often read as a mildly bearish "
            f"contrarian signal."
        )
    else:
        return (
            f"PCR is {pcr:.2f} — close to neutral (typically read as the 0.7-1.3 band). "
            f"No strong directional bias from options positioning right now."
        )


# ---------------------------------------------------------------------------
# Max Pain
# ---------------------------------------------------------------------------

def calculate_max_pain(strikes: list[StrikeOI]) -> float:
    """
    Max Pain: the strike price at which option WRITERS (sellers) collectively
    face the smallest total payout obligation if the underlying settles
    there at expiry — the classic theory being that price tends to gravitate
    toward this level as option sellers (who dominate open interest) have
    an economic interest in it settling there.

    For each CANDIDATE settlement price K (we test every actual listed
    strike as a candidate, which is standard practice — the true max pain
    point is always one of the listed strikes), total payout to option
    BUYERS (i.e., cost to writers) is:
        sum over all strikes Si:
            call_oi(Si) * max(K - Si, 0)   [ITM calls if K > Si]
          + put_oi(Si)  * max(Si - K, 0)   [ITM puts if Si > K]
    Max pain = the K that MINIMIZES this total payout.
    """
    if not strikes:
        raise ValueError("Cannot calculate max pain on an empty strike list")

    candidate_strikes = [s["strike"] for s in strikes]
    best_strike = None
    best_payout = None

    for k in candidate_strikes:
        total_payout = 0.0
        for s in strikes:
            si = s["strike"]
            total_payout += s["call_oi"] * max(k - si, 0)
            total_payout += s["put_oi"] * max(si - k, 0)

        if best_payout is None or total_payout < best_payout:
            best_payout = total_payout
            best_strike = k

    return best_strike


def interpret_max_pain(max_pain_strike: float, spot: float) -> str:
    distance = spot - max_pain_strike
    direction = "above" if distance > 0 else "below" if distance < 0 else "at"
    return (
        f"Max Pain is at strike {max_pain_strike:,.0f}, {abs(distance):,.0f} points "
        f"{direction} the current spot of {spot:,.0f}. Max pain theory suggests price "
        f"may gravitate toward this level as expiry approaches — a commonly-cited "
        f"heuristic, not a guaranteed outcome."
    )


# ---------------------------------------------------------------------------
# DOS Trade Interpretation Card
# ---------------------------------------------------------------------------

class TradeForCard(TypedDict, total=False):
    option_side: str  # "CE" or "PE"
    strike: float
    day_type: str  # "wednesday" or "thursday"
    entry_premium: float
    current_premium: Optional[float]
    just_flipped: bool
    is_open: bool
    exit_reason: Optional[str]  # "initial_sl", "trailing_sl", "market_close", or None if still open
    pnl: Optional[float]


def generate_dos_trade_card(trade: TradeForCard) -> str:
    """
    Auto-generated plain-language summary of a DOS trade, per spec:
    "One plain-language DOS interpretation card per live trade" e.g.
    "Sold 52000 CE on Thursday at ₹190 — SuperTrend flipped down, initial
    SL 100% hit due to a sharp reversal at 11:40 AM."

    Handles both an OPEN (still live) trade and a CLOSED (exited) trade,
    since the shape of what's worth saying differs between the two.
    """
    side_verb = "Sold"
    option_desc = f"{trade['strike']:,.0f} {trade['option_side']}"
    day_label = trade["day_type"].capitalize()
    entry_desc = f"at ₹{trade['entry_premium']:.2f}"
    day_sl_note = "50% initial SL" if trade["day_type"] == "wednesday" else "100% initial SL"

    if trade.get("is_open", True) and trade.get("exit_reason") is None:
        current = trade.get("current_premium")
        if current is not None:
            direction = "in the seller's favor" if current < trade["entry_premium"] else "against the seller"
            return (
                f"{side_verb} {option_desc} on {day_label} {entry_desc} — currently active "
                f"at ₹{current:.2f} ({direction}), {day_sl_note} rule applies. Position remains open."
            )
        return (
            f"{side_verb} {option_desc} on {day_label} {entry_desc} — currently active, "
            f"{day_sl_note} rule applies. Position remains open."
        )

    # Closed trade
    reason_map = {
        "initial_sl": "the initial stop-loss was hit",
        "trailing_sl": "SuperTrend flipped against the position (trailing SL)",
        "market_close": "held to market close with no SL triggered",
    }
    reason_text = reason_map.get(trade.get("exit_reason"), "the position was closed")
    pnl = trade.get("pnl")
    pnl_text = ""
    if pnl is not None:
        outcome = "profit" if pnl >= 0 else "loss"
        pnl_text = f" Result: ₹{abs(pnl):,.2f} {outcome}."

    return (
        f"{side_verb} {option_desc} on {day_label} {entry_desc} — {reason_text}.{pnl_text}"
    )
