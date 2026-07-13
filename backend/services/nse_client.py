import logging
import requests
import time
from typing import Dict, Any

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
    """Generates realistic mock data for NIFTY or BANKNIFTY on fallback."""
    symbol_upper = symbol.upper()
    if "BANK" in symbol_upper:
        underlying = 52300.0
        strikes = [52100, 52200, 52300, 52400, 52500]
    else:
        underlying = 24300.0
        strikes = [24100, 24200, 24300, 24400, 24500]

    data = []
    for strike in strikes:
        # Simple option pricing model for realistic looking mock prices
        # ATM options cost ~100/200, ITM options capture intrinsic value
        ce_price = max(underlying - strike, 0.0) + max(120.0 - abs(underlying - strike) * 0.6, 5.0)
        pe_price = max(strike - underlying, 0.0) + max(120.0 - abs(underlying - strike) * 0.6, 5.0)

        data.append({
            "strikePrice": strike,
            "expiryDate": "2026-07-16",
            "CE": {
                "strikePrice": strike,
                "expiryDate": "2026-07-16",
                "underlying": symbol_upper,
                "identifier": f"OPT{symbol_upper}16-07-2026CE{strike}",
                "openInterest": 25000,
                "changeinOpenInterest": 1500,
                "totalTradedVolume": 65000,
                "impliedVolatility": 13.5,
                "lastPrice": round(ce_price, 2),
                "underlyingValue": underlying
            },
            "PE": {
                "strikePrice": strike,
                "expiryDate": "2026-07-16",
                "underlying": symbol_upper,
                "identifier": f"OPT{symbol_upper}16-07-2026PE{strike}",
                "openInterest": 30000,
                "changeinOpenInterest": 2200,
                "totalTradedVolume": 85000,
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
