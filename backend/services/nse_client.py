import logging
import requests
import time
from typing import Dict, Any

try:
    from ..core.bsm import bs_price
except ImportError:
    from core.bsm import bs_price

logger = logging.getLogger(__name__)

# Realistic Chrome Headers Setup
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)

HEADERS_COMMON = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

def get_mock_data(symbol: str) -> Dict[str, Any]:
    """Generates realistic mock data for NIFTY or BANKNIFTY on fallback.
    Spot price is fetched live via yfinance (unaffected by the NSE/Akamai
    block) so mock strikes stay centered near the real market, instead of
    drifting stale relative to wherever the index actually is now."""
    import yfinance as yf
    import logging
    logger = logging.getLogger(__name__)

    symbol_upper = symbol.upper()
    ticker_map = {"BANKNIFTY": "^NSEBANK", "NIFTY": "^NSEI"}
    yf_ticker = ticker_map.get(symbol_upper if symbol_upper in ticker_map else ("BANKNIFTY" if "BANK" in symbol_upper else "NIFTY"))

    fallback_underlying = 52300.0 if "BANK" in symbol_upper else 24300.0

    try:
        ticker = yf.Ticker(yf_ticker)
        hist = ticker.history(period="1d", interval="5m")
        if not hist.empty:
            underlying = float(hist["Close"].iloc[-1])
        else:
            logger.warning(f"get_mock_data: yfinance returned empty history for {yf_ticker}, using fallback spot price")
            underlying = fallback_underlying
    except Exception as e:
        logger.warning(f"get_mock_data: failed to fetch live spot for {yf_ticker}, using fallback spot price. Error: {e}")
        underlying = fallback_underlying

    import random
    import math

    # Add small realistic tick-to-tick fluctuation (+/- 0.05%) so repeated polls
    # don't show frozen, identical numbers during a demo — real quotes always
    # show small movement between ticks even when the market is calm.
    fluctuation_pct = random.uniform(-0.0005, 0.0005)
    underlying = underlying * (1 + fluctuation_pct)

    # Round to nearest 100, generate 5 strikes centered on that (2 below, ATM, 2 above)
    atm_strike = round(underlying / 100) * 100
    strikes = [atm_strike + offset for offset in (-200, -100, 0, 100, 200)]

    data = []
    ASSUMED_MOCK_IV = 0.13  # 13%, realistic ballpark for Bank Nifty weekly IV
    ASSUMED_MOCK_RISK_FREE_RATE = 0.07  # matches the MIBOR-proxy value used elsewhere in core/bsm tests
    ASSUMED_MOCK_TIME_TO_EXPIRY = 3 / 365  # ~3 days, typical for a weekly expiry mock scenario

    for strike in strikes:
        ce_price = bs_price(
            S=underlying, K=strike, T=ASSUMED_MOCK_TIME_TO_EXPIRY,
            r=ASSUMED_MOCK_RISK_FREE_RATE, sigma=ASSUMED_MOCK_IV, option_type="call",
        )
        pe_price = bs_price(
            S=underlying, K=strike, T=ASSUMED_MOCK_TIME_TO_EXPIRY,
            r=ASSUMED_MOCK_RISK_FREE_RATE, sigma=ASSUMED_MOCK_IV, option_type="put",
        )
        # Floor at a small positive value so deep OTM strikes never show as free/zero
        ce_price = max(ce_price, 1.0)
        pe_price = max(pe_price, 1.0)

        # Scale OI so it peaks near ATM and tapers off
        distance_from_atm = abs(strike - underlying)
        base_oi = 50000
        ce_oi = int(base_oi * math.exp(-0.5 * (distance_from_atm / (underlying * 0.02))**2)) + random.randint(100, 500)
        pe_oi = int(base_oi * math.exp(-0.5 * (distance_from_atm / (underlying * 0.02))**2)) + random.randint(100, 500)

        data.append({
            "strikePrice": strike,
            "expiryDate": "2026-07-16",
            "CE": {
                "strikePrice": strike,
                "expiryDate": "2026-07-16",
                "underlying": symbol_upper,
                "identifier": f"OPT{symbol_upper}16-07-2026CE{strike}",
                "openInterest": ce_oi,
                "changeinOpenInterest": int(ce_oi * 0.06),
                "totalTradedVolume": int(ce_oi * 2.6),
                "impliedVolatility": 13.5,
                "lastPrice": round(ce_price, 2),
                "underlyingValue": underlying
            },
            "PE": {
                "strikePrice": strike,
                "expiryDate": "2026-07-16",
                "underlying": symbol_upper,
                "identifier": f"OPT{symbol_upper}16-07-2026PE{strike}",
                "openInterest": pe_oi,
                "changeinOpenInterest": int(pe_oi * 0.07),
                "totalTradedVolume": int(pe_oi * 2.8),
                "impliedVolatility": 14.2,
                "lastPrice": round(pe_price, 2),
                "underlyingValue": underlying
            }
        })

    return {
        "source": "mock",
        "records": {
            "expiryDates": ["2026-07-16", "2026-07-23"],
            "underlyingValue": underlying,
            "timestamp": "13-Jul-2026 15:30:00",
            "data": data
        },
        "filtered": {
            "data": data
        }
    }

def get_option_chain(symbol: str = "NIFTY") -> Dict[str, Any]:
    """
    Fetch option chain data from NSE India index API.
    Attempts a realistic 3-step navigation flow with Chrome headers and delays.
    Falls back to mock data on any exception.
    """
    symbol_upper = symbol.upper()
    session = requests.Session()
    
    url_home = "https://www.nseindia.com"
    url_opt_chain = "https://www.nseindia.com/option-chain"
    url_api = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol_upper}"
    
    # Step a: Visit homepage
    headers_home = {
        **HEADERS_COMMON,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    }
    
    # Step c: Visit option chain HTML page
    headers_opt_chain = {
        **HEADERS_COMMON,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Upgrade-Insecure-Requests": "1",
        "Referer": url_home,
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    }
    
    # Step e: Request JSON API
    headers_api = {
        **HEADERS_COMMON,
        "Accept": "application/json, text/plain, */*",
        "Referer": url_opt_chain,
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }
    
    try:
        # Step a: Homepage GET
        logger.info(f"[NSE Flow Step A] Visiting homepage {url_home}...")
        r_home = session.get(url_home, headers=headers_home, timeout=10)
        logger.info(f"[NSE Flow Step A Response] Status: {r_home.status_code}, Body (first 200 char): {r_home.text[:200]!r}")
        r_home.raise_for_status()
        
        # Step b: 1.5s delay
        logger.info("[NSE Flow Step B] Sleeping for 1.5 seconds...")
        time.sleep(1.5)
        
        # Step c: Option Chain HTML GET
        logger.info(f"[NSE Flow Step C] Visiting option chain HTML {url_opt_chain}...")
        r_opt_chain = session.get(url_opt_chain, headers=headers_opt_chain, timeout=10)
        logger.info(f"[NSE Flow Step C Response] Status: {r_opt_chain.status_code}, Body (first 200 char): {r_opt_chain.text[:200]!r}")
        r_opt_chain.raise_for_status()
        
        # Step d: 1.0s delay
        logger.info("[NSE Flow Step D] Sleeping for 1.0 seconds...")
        time.sleep(1.0)
        
        # Step e: API JSON GET
        logger.info(f"[NSE Flow Step E] Requesting API JSON {url_api}...")
        r_api = session.get(url_api, headers=headers_api, timeout=10)
        logger.info(f"[NSE Flow Step E Response] Status: {r_api.status_code}, Body (first 200 char): {r_api.text[:200]!r}")
        r_api.raise_for_status()
        
        data = r_api.json()
        data["source"] = "live"
        strike_count = len(data.get("records", {}).get("data", []))
        logger.info(f"Successfully fetched live option chain for {symbol_upper} containing {strike_count} strikes.")
        return data
        
    except Exception as e:
        logger.error(
            f"Failed to fetch live option chain for {symbol_upper} due to error: {str(e)}. "
            f"Falling back to mock data."
        )
        return get_mock_data(symbol_upper)
