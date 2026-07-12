from fastapi import APIRouter, HTTPException, Query
from backend.services import nse_client, yfinance_client

router = APIRouter(prefix="/api", tags=["Market Data"])

@router.get("/option-chain")
def get_option_chain(symbol: str = Query("NIFTY", description="Option chain asset symbol (e.g. NIFTY)")):
    """Fetch option chain data for NIFTY or other indices with automatic mock fallback on failure."""
    return nse_client.get_option_chain(symbol)

@router.get("/spot")
def get_spot_price(ticker: str = Query("^NSEI", description="Yahoo Finance ticker symbol (e.g. ^NSEI)")):
    """Fetch the latest spot price for a given ticker."""
    try:
        price = yfinance_client.get_spot_price(ticker)
        return {
            "ticker": ticker,
            "spot_price": price
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch spot price for {ticker}: {str(e)}"
        )
