import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Realistic desktop Chrome User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

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
    Fetch option chain data from NSE India.
    If the request fails or is blocked, logs the error and falls back to mock data.
    """
    symbol_upper = symbol.upper()
    session = requests.Session()
    
    # Phase 1: Initialize cookies by visiting the homepage
    headers_home = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Phase 2: Call the option chain API endpoint
    headers_api = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }
    
    url_home = "https://www.nseindia.com"
    url_api = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol_upper}"
    
    try:
        logger.info(f"Visiting homepage {url_home} to establish cookies...")
        r_home = session.get(url_home, headers=headers_home, timeout=10)
        r_home.raise_for_status()
        
        logger.info(f"Requesting option chain data for {symbol_upper} from {url_api}...")
        r_api = session.get(url_api, headers=headers_api, timeout=10)
        r_api.raise_for_status()
        
        data = r_api.json()
        data["source"] = "live"
        logger.info(f"Successfully fetched live option chain for {symbol_upper}.")
        return data
        
    except Exception as e:
        logger.error(
            f"Failed to fetch live option chain for {symbol_upper} due to error: {str(e)}. "
            f"Falling back to mock data."
        )
        return get_mock_data(symbol_upper)
