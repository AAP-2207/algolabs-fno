import os
import logging
import datetime
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel

try:
    from ..services import nse_client, yfinance_client
except ImportError:
    from services import nse_client, yfinance_client

try:
    from ..core.greeks import delta, gamma, theta, vega
    from ..core.iv_solver import implied_volatility
except ImportError:
    from core.greeks import delta, gamma, theta, vega
    from core.iv_solver import implied_volatility

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

# P&L Decomposer Request Schema
class PnlDecomposeRequest(BaseModel):
    strike: float
    option_type: str # "CE" or "PE"
    position: str # "buy" or "sell"
    quantity: int
    entry_price: float
    current_price: float
    current_S: float
    previous_S: float
    days_elapsed: float
    volatility: float = 0.15 # Volatility input (decimal, e.g. 0.15)
    days_to_expiry: float = 30.0 # Time to expiry at previous state
    current_volatility: float = None # To calculate vega_pnl if provided

@router.get("/greeks")
def get_greeks(symbol: str = Query("NIFTY", description="Option chain symbol (e.g. NIFTY)")):
    """Fetch options chain and compute Greeks & IV for each strike."""
    symbol_upper = symbol.upper()
    current_time = datetime.datetime.now(datetime.timezone.utc)
    current_date = current_time.date()
    r = 0.06 # MIBOR-proxy rate (6%)

    chain_data = None
    fetched_at = None
    source = "mock"
    age_minutes = 0.0

    if supabase_client is not None:
        try:
            logger.info(f"Querying Supabase for option chain snapshot of {symbol_upper} for Greeks...")
            response = supabase_client.table("option_chain_snapshots") \
                .select("data, fetched_at") \
                .eq("symbol", symbol_upper) \
                .order("fetched_at", desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                record = response.data[0]
                chain_data = record.get("data")
                fetched_at = record.get("fetched_at")
                if isinstance(chain_data, dict):
                    source = "live-polled"
                    try:
                        fetched_dt = datetime.datetime.fromisoformat(fetched_at)
                        if fetched_dt.tzinfo is None:
                            fetched_dt = fetched_dt.replace(tzinfo=datetime.timezone.utc)
                        age_minutes = (current_time - fetched_dt).total_seconds() / 60.0
                    except Exception as parse_err:
                        logger.error(f"Error parsing fetched_at '{fetched_at}': {parse_err}")
                        age_minutes = 0.0
                else:
                    chain_data = None
        except Exception as e:
            logger.error(f"Error querying Supabase for Greeks: {str(e)}")

    if chain_data is None:
        logger.info(f"Falling back to direct fetch for Greeks symbol {symbol_upper}...")
        chain_data = nse_client.get_option_chain(symbol_upper)
        fetched_at = current_time.isoformat()
        source = "mock"
        age_minutes = 0.0

    # Parse and compute
    strikes_res = []
    records = chain_data.get("records", {})
    underlying_value = records.get("underlyingValue") or 0.0
    raw_data = records.get("data", [])

    for item in raw_data:
        strike_price = item.get("strikePrice")
        expiry_date_str = item.get("expiryDate")
        
        # Calculate time to expiry T
        try:
            expiry_dt = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        except Exception:
            try:
                expiry_dt = datetime.date.fromisoformat(expiry_date_str)
            except Exception:
                expiry_dt = current_date
        
        days_to_expiry = (expiry_dt - current_date).days
        T = max(days_to_expiry, 1.0) / 365.0

        ce_res = None
        pe_res = None

        for option_side in ("CE", "PE"):
            opt_data = item.get(option_side)
            if not opt_data:
                continue

            ltp = opt_data.get("lastPrice") or 0.0
            nse_iv = opt_data.get("impliedVolatility") or 0.0
            
            # Default fallback values
            solved_iv = 0.0
            sigma = 0.15 # fallback default
            
            if ltp > 0 and underlying_value > 0 and strike_price > 0:
                try:
                    solved_vol = implied_volatility(ltp, underlying_value, strike_price, T, r, 'call' if option_side == "CE" else 'put')
                    solved_iv = solved_vol * 100.0
                    sigma = solved_vol
                except Exception as e:
                    # Fallback to NSE IV if available, else standard 15%
                    if nse_iv > 0:
                        sigma = nse_iv / 100.0
                    else:
                        sigma = 0.15
            else:
                if nse_iv > 0:
                    sigma = nse_iv / 100.0

            # Compute Greeks
            try:
                d_val = delta(underlying_value, strike_price, T, r, sigma, 'call' if option_side == "CE" else 'put')
                g_val = gamma(underlying_value, strike_price, T, r, sigma)
                t_val = theta(underlying_value, strike_price, T, r, sigma, 'call' if option_side == "CE" else 'put')
                v_val = vega(underlying_value, strike_price, T, r, sigma)
            except Exception as e:
                logger.error(f"Greeks calculation failed for {option_side} strike {strike_price}: {e}")
                d_val, g_val, t_val, v_val = 0.0, 0.0, 0.0, 0.0

            res_dict = {
                "delta": d_val,
                "gamma": g_val,
                "theta": t_val,
                "vega": v_val,
                "computed_iv": solved_iv,
                "nse_iv": nse_iv,
                "ltp": ltp
            }

            if option_side == "CE":
                ce_res = res_dict
            else:
                pe_res = res_dict

        strikes_res.append({
            "strike": strike_price,
            "CE": ce_res,
            "PE": pe_res
        })

    return {
        "fetched_at": fetched_at,
        "source": source,
        "age_minutes": age_minutes,
        "strikes": strikes_res
    }

@router.post("/pnl-decompose")
def pnl_decompose(req: PnlDecomposeRequest):
    """Decompose position P&L into Greeks contribution components."""
    sign = -1 if req.position.lower() == "sell" else 1
    
    # 1. Compute total actual price-based P&L
    total_pnl = (req.current_price - req.entry_price) * req.quantity * sign

    # 2. Setup Greeks parameters (at previous state)
    S = req.previous_S
    K = req.strike
    T_previous = max(req.days_to_expiry, 1.0) / 365.0
    r = 0.06
    sigma = req.volatility

    # 3. Compute Greeks (at previous state)
    opt_type_lower = "call" if req.option_type.upper() == "CE" else "put"
    try:
        delta_val = delta(S, K, T_previous, r, sigma, opt_type_lower)
        gamma_val = gamma(S, K, T_previous, r, sigma)
        theta_val = theta(S, K, T_previous, r, sigma, opt_type_lower)
        vega_val = vega(S, K, T_previous, r, sigma)
    except Exception as e:
        logger.error(f"Failed to calculate Greeks for P&L decompose: {e}")
        delta_val, gamma_val, theta_val, vega_val = 0.0, 0.0, 0.0, 0.0

    # 4. Decompose P&L using first-order Taylor expansion
    dS = req.current_S - req.previous_S
    
    delta_pnl = delta_val * dS * req.quantity * sign
    gamma_pnl = 0.5 * gamma_val * (dS ** 2) * req.quantity * sign
    theta_pnl = theta_val * req.days_elapsed * req.quantity * sign
    
    d_sigma = (req.current_volatility - req.volatility) if req.current_volatility is not None else 0.0
    vega_pnl = vega_val * d_sigma * req.quantity * sign

    # Residual P&L
    residual = total_pnl - (delta_pnl + gamma_pnl + theta_pnl + vega_pnl)

    # 5. Build dynamic plain-English summary
    pnl_contribs = [
        ("Delta movement", delta_pnl),
        ("Gamma acceleration", gamma_pnl),
        ("Theta time decay", theta_pnl),
        ("Vega volatility shift", vega_pnl)
    ]
    pnl_contribs.sort(key=lambda x: abs(x[1]), reverse=True)
    top = pnl_contribs[0]
    sec = pnl_contribs[1]
    
    summary = (
        f"Most of this trade's P&L came from {top[0]} (₹{top[1]:.2f}), "
        f"with {sec[0]} contributing Z."
    )
    # Correcting "contributing Z" to second contributor's value as per user format
    summary = summary.replace("Z", f"₹{sec[1]:.2f}")

    return {
        "total_pnl": float(total_pnl),
        "delta_pnl": float(delta_pnl),
        "gamma_pnl": float(gamma_pnl),
        "theta_pnl": float(theta_pnl),
        "vega_pnl": float(vega_pnl),
        "residual": float(residual),
        "summary": summary
    }
