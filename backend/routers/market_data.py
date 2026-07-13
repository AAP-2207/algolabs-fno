import os
import logging
import datetime
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv
from supabase import create_client, Client
try:
    from ..services import nse_client, yfinance_client
except ImportError:
    from services import nse_client, yfinance_client

logger = logging.getLogger(__name__)

# Load env variables for local execution and testing
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

# Standardize Supabase URL (strip trailing rest/v1 or rest/v1/ paths)
if supabase_url and (supabase_url.endswith("/rest/v1/") or supabase_url.endswith("/rest/v1")):
    supabase_url = supabase_url.replace("/rest/v1/", "").replace("/rest/v1", "")

supabase_client: Client = None
if supabase_url and supabase_key:
    try:
        supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully in market_data router.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")

router = APIRouter(prefix="/api", tags=["Market Data"])

@router.get("/option-chain")
def get_option_chain(symbol: str = Query("NIFTY", description="Option chain asset symbol (e.g. NIFTY)")):
    """Fetch option chain data for NIFTY or other indices, querying Supabase first and falling back to nse_client."""
    symbol_upper = symbol.upper()
    current_time = datetime.datetime.now(datetime.timezone.utc)
    if supabase_client is not None:
        try:
            logger.info(f"Querying Supabase for option chain snapshot of {symbol_upper}...")
            response = supabase_client.table("option_chain_snapshots") \
                .select("data, fetched_at") \
                .eq("symbol", symbol_upper) \
                .order("fetched_at", desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                record = response.data[0]
                data = record.get("data")
                fetched_at = record.get("fetched_at")
                
                if isinstance(data, dict):
                    # Calculate age_minutes fresh on each request
                    try:
                        fetched_dt = datetime.datetime.fromisoformat(fetched_at)
                        if fetched_dt.tzinfo is None:
                            fetched_dt = fetched_dt.replace(tzinfo=datetime.timezone.utc)
                        age_minutes = (current_time - fetched_dt).total_seconds() / 60.0
                    except Exception as parse_err:
                        logger.error(f"Error parsing fetched_at '{fetched_at}': {parse_err}")
                        age_minutes = 0.0
                    
                    logger.info(f"Serving option chain from Supabase snapshot fetched at {fetched_at} ({age_minutes:.2f} minutes old).")
                    
                    return {
                        "data": data,
                        "fetched_at": fetched_at,
                        "source": "live-polled",
                        "age_minutes": age_minutes
                    }
                else:
                    logger.warning("Found record in Supabase, but 'data' column is not a JSON object.")
            else:
                logger.warning(f"No option chain snapshots found in Supabase for symbol {symbol_upper}.")
        except Exception as e:
            logger.error(f"Error querying Supabase for symbol {symbol_upper}: {str(e)}. Falling back to direct fetch.")
            
    # Last-resort fallback
    logger.info(f"Falling back to direct fetch for symbol {symbol_upper}...")
    nse_data = nse_client.get_option_chain(symbol_upper)
    return {
        "data": nse_data,
        "fetched_at": current_time.isoformat(),
        "source": "mock",
        "age_minutes": 0.0
    }

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
