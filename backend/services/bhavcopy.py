"""
backend/services/bhavcopy.py

Fetches and parses NSE's F&O UDiFF Bhavcopy (the current format since
July 2024 — the old fo*.csv format was discontinued). Confirmed reachable
directly from Render (no proxy/workaround needed, unlike the live
option-chain API), so this can run on-demand in production.

URL pattern confirmed via NSE's own site + cross-referenced against two
independent open-source NSE data tools:
  https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip

IMPORTANT CONTEXT: Bank Nifty WEEKLY options were discontinued by SEBI
directive effective Nov 20, 2024. This module is intended for BACKTESTING
against historical dates when Bank Nifty weekly options were active:
  - Thursday expiry: May 2016 -> September 2023
  - Wednesday expiry: September 2023 -> November 2024
Pick backtest dates from this window, not from any recent date.
"""

import io
import zipfile
from datetime import date
from typing import Optional

import pandas as pd
import requests

BHAVCOPY_URL_TEMPLATE = (
    "https://nsearchives.nseindia.com/content/fo/"
    "BhavCopy_NSE_FO_0_0_0_{date_str}_F_0000.csv.zip"
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Columns we actually need — the raw file has ~34 columns, most irrelevant
# to this project (settlement/session/reserved fields etc.)
#
# IMPORTANT — SttlmPric is NOT the option contract's settlement price.
# Verified against live NSE data (Feb 7 2024): SttlmPric shows the SAME
# value (e.g. 45818.50) across every strike and option type for a given
# trade date — it is the UNDERLYING INDEX's daily settlement price, not
# the individual option's closing/settlement premium.
#
# For any P&L or backtest calculation, use ClsPric (the option's closing
# price), which was confirmed to show sane, strike-appropriate premiums
# (e.g. same-day 47400 CE closed at 0.10, deep ITM 43900 CE at 1913.80).
# SttlmPric is retained here for reference/debugging only — do NOT use it
# as an option price in any pricing or greeks logic.
RELEVANT_COLUMNS = [
    "TradDt", "TckrSymb", "XpryDt", "StrkPric", "OptnTp",
    "OpnPric", "HghPric", "LwPric", "ClsPric",
    "SttlmPric",      # WARNING: underlying index settlement price, NOT option price — see note above
    "OpnIntrst", "TtlTradgVol",
]


class BhavcopyFetchError(Exception):
    """Raised when a Bhavcopy file can't be fetched or parsed for a given date."""
    pass


def fetch_bhavcopy_raw(trade_date: date, timeout: int = 20) -> bytes:
    """
    Downloads the raw zip bytes for a given trade date. Raises
    BhavcopyFetchError with a clear message on failure (bad status,
    network error, or non-trading day where NSE simply has no file).
    """
    date_str = trade_date.strftime("%Y%m%d")
    url = BHAVCOPY_URL_TEMPLATE.format(date_str=date_str)

    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    except requests.RequestException as e:
        raise BhavcopyFetchError(f"Network error fetching Bhavcopy for {trade_date}: {e}")

    if response.status_code == 404:
        raise BhavcopyFetchError(
            f"No Bhavcopy file for {trade_date} (404) — likely a weekend, "
            f"holiday, or a date NSE hasn't published data for yet."
        )
    if response.status_code != 200:
        raise BhavcopyFetchError(
            f"Unexpected status {response.status_code} fetching Bhavcopy for {trade_date}"
        )

    content_type = response.headers.get("Content-Type", "")
    if "zip" not in content_type.lower():
        raise BhavcopyFetchError(
            f"Expected a zip file for {trade_date}, got Content-Type={content_type!r}. "
            f"NSE may have changed the URL format again — verify manually."
        )

    return response.content


def parse_bhavcopy_zip(raw_bytes: bytes) -> pd.DataFrame:
    """
    Unzips the raw bytes and parses the inner CSV, returning only the
    columns this project needs.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise BhavcopyFetchError("Zip file contained no CSV — unexpected archive contents")
            with zf.open(csv_names[0]) as csv_file:
                df = pd.read_csv(csv_file)
    except zipfile.BadZipFile as e:
        raise BhavcopyFetchError(f"Downloaded file is not a valid zip: {e}")

    missing = [c for c in RELEVANT_COLUMNS if c not in df.columns]
    if missing:
        raise BhavcopyFetchError(
            f"Expected columns missing from Bhavcopy CSV: {missing}. "
            f"NSE may have changed the schema — actual columns were: {list(df.columns)}"
        )

    return df[RELEVANT_COLUMNS].copy()


def get_banknifty_options(
    trade_date: date,
    expiry_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Fetches and filters a single trade date's Bhavcopy down to BANKNIFTY
    options only (excludes futures, which have OptnTp == 'XX').

    If expiry_date is given, filters to just that one expiry (use this
    for weekly-options backtesting to isolate a specific expiry week's
    contracts from the many expiries present in any single day's file).
    """
    raw = fetch_bhavcopy_raw(trade_date)
    df = parse_bhavcopy_zip(raw)

    df = df[df["TckrSymb"] == "BANKNIFTY"].copy()
    df = df[df["OptnTp"].isin(["CE", "PE"])].copy()

    if df.empty:
        raise BhavcopyFetchError(
            f"No BANKNIFTY option rows found for {trade_date}. This could mean: "
            f"(a) the date is outside the window when Bank Nifty weekly options "
            f"existed (May 2016 - Nov 2024), or (b) it's a non-trading day."
        )

    df["XpryDt"] = pd.to_datetime(df["XpryDt"], errors="coerce")
    df["TradDt"] = pd.to_datetime(df["TradDt"], errors="coerce")

    if expiry_date is not None:
        available_expiries = sorted(df["XpryDt"].dt.date.unique())
        df = df[df["XpryDt"].dt.date == expiry_date].copy()
        if df.empty:
            raise BhavcopyFetchError(
                f"No BANKNIFTY rows for expiry_date={expiry_date} on trade_date={trade_date}. "
                f"Available expiries in this file were: {available_expiries}. "
                f"Check the expiry date is correct for this week (Bank Nifty weekly expiry "
                f"was Thursday before Sep 2023, Wednesday after)."
            )

    return df.reset_index(drop=True)
