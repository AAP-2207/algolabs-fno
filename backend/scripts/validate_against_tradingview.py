"""
backend/scripts/validate_against_tradingview.py

Run this once you've placed core/supertrend.py in your repo. It pulls real
Bank Nifty 5-min candles (via yfinance, NOT affected by the NSE/Akamai
block — this is separate infrastructure), computes SuperTrend, and writes
a CSV so you can manually cross-check flip points against TradingView.

USAGE:
    cd backend
    python scripts/validate_against_tradingview.py

This does NOT auto-verify against TradingView (no API for that) — the
manual cross-check is a required step you do by eye. This script just
gets your data + computed values into a form that's fast to compare.

HOW TO CROSS-CHECK (do this before Phase 8):
1. Open TradingView, chart ^NSEBANK (or Bank Nifty futures if you have
   access), set timeframe to 5 min.
2. Add the built-in "Supertrend" indicator, set ATR Length = 10,
   Factor/Multiplier = 3 (matches the DOS spec exactly).
3. Pick a date range that appears in the CSV this script produces.
4. Compare 5-10 flip points (where trend switches up/down) between your
   CSV's `trend_flip == True` rows and where TradingView's SuperTrend
   line visibly changes color/side.
5. They should match on the same bar (or be off by at most one bar due to
   minor OHLC data-source differences between yfinance and TradingView's
   own feed — more than 1 bar off, or a systematically wrong direction,
   means stop and debug before touching any DOS UI).
"""

import sys
import pandas as pd
import yfinance as yf

sys.path.insert(0, ".")  # so `from core.supertrend import ...` resolves when run from backend/
from core.supertrend import calculate_supertrend  # noqa: E402


def fetch_bank_nifty_5min(period: str = "5d") -> pd.DataFrame:
    """
    yfinance only allows 5-min interval data for the last ~60 days, and
    typically only returns a handful of recent days reliably at once —
    `period='5d'` or `'1mo'` are safe starting points. ^NSEBANK is the
    Bank Nifty index; if you specifically need Bank Nifty FUTURES (per
    spec) rather than the index, you'll eventually want Bhav Copy futures
    data for full accuracy, but the index is a reasonable proxy for
    validating the SuperTrend *logic* itself since it moves near-identically
    intraday.
    """
    ticker = yf.Ticker("^NSEBANK")
    df = ticker.history(period=period, interval="5m")

    if df.empty:
        raise RuntimeError(
            "yfinance returned no data for ^NSEBANK at 5m interval. "
            "Try a shorter period, or check yfinance isn't rate-limited."
        )

    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low", "Close": "close",
    })
    df = df[["open", "high", "low", "close"]]
    df.index = df.index.tz_localize(None) if df.index.tz is not None else df.index
    return df


def main():
    print("Fetching Bank Nifty 5-min candles via yfinance...")
    df = fetch_bank_nifty_5min(period="5d")
    print(f"Got {len(df)} candles from {df.index[0]} to {df.index[-1]}")

    result = calculate_supertrend(df, period=10, multiplier=3)

    out_path = "supertrend_validation_output.csv"
    result[["open", "high", "low", "close", "atr", "supertrend", "trend", "trend_flip"]].to_csv(out_path)
    print(f"Wrote {out_path}")

    flips = result[result["trend_flip"]]
    print(f"\n{len(flips)} real trend flips detected (warm-up rows excluded). Flip points to cross-check against TradingView:\n")
    for ts, row in flips.iterrows():
        direction = "-> UP (BNF > ST, sell CE)" if row["trend"] == "up" else "-> DOWN (BNF < ST, sell PE)"
        print(f"  {ts}  close={row['close']:.1f}  ST={row['supertrend']:.1f}  {direction}")

    print(
        "\nNext: open TradingView, chart ^NSEBANK 5-min, add Supertrend "
        "(ATR Length=10, Factor=3), and confirm these flip timestamps match "
        "within 1 bar. If more than 1 bar off, or direction is systematically "
        "wrong, stop and debug before Phase 8."
    )


if __name__ == "__main__":
    main()
