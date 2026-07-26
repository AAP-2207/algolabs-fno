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
                        age_minutes = 999.0

                    # Check if snapshot is reasonably fresh (<= 60 mins) and contains strike records
                    records_data = data.get("records", {}).get("data", []) if isinstance(data, dict) else []
                    if age_minutes <= 60.0 and len(records_data) >= 3:
                        logger.info(f"Serving option chain from Supabase snapshot fetched at {fetched_at} ({age_minutes:.2f} minutes old).")
                        return {
                            "data": data,
                            "fetched_at": fetched_at,
                            "source": "live-polled",
                            "age_minutes": age_minutes
                        }
                    else:
                        logger.warning(f"Supabase snapshot for {symbol_upper} is stale ({age_minutes:.1f}m old > 60m threshold) or has incomplete strikes ({len(records_data)} strikes). Falling back to fresh nse_client data.")
                else:
                    logger.warning("Found record in Supabase, but 'data' column is not a JSON object.")
            else:
                logger.warning(f"No option chain snapshots found in Supabase for symbol {symbol_upper}.")
        except Exception as e:
            logger.error(f"Error querying Supabase for symbol {symbol_upper}: {str(e)}. Falling back to direct fetch.")
            
    # Last-resort fallback to fresh nse_client mock data
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
                    try:
                        fetched_dt = datetime.datetime.fromisoformat(fetched_at)
                        if fetched_dt.tzinfo is None:
                            fetched_dt = fetched_dt.replace(tzinfo=datetime.timezone.utc)
                        age_minutes = (current_time - fetched_dt).total_seconds() / 60.0
                    except Exception as parse_err:
                        logger.error(f"Error parsing fetched_at '{fetched_at}': {parse_err}")
                        age_minutes = 999.0

                    records_data = chain_data.get("records", {}).get("data", []) if isinstance(chain_data, dict) else []
                    if age_minutes <= 60.0 and len(records_data) >= 3:
                        source = "live-polled"
                    else:
                        logger.warning(f"Supabase snapshot for Greeks {symbol_upper} is stale ({age_minutes:.1f}m old > 60m) or incomplete. Falling back to fresh nse_client data.")
                        chain_data = None
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

@router.get("/vol-surface")
def get_vol_surface(symbol: str = Query("NIFTY", description="Option chain symbol (e.g. NIFTY)")):
    """
    Fetch multi-expiry option chain data and compute 3D Volatility Surface points
    (Strikes x Expiry Dates x Implied Volatility).
    
    Uses existing, tested implied_volatility solver function from core/iv_solver.py.
    Applies liquidity and sanity filters (open_interest >= 50, ltp >= 1.0, 3.0% <= IV <= 150.0%).
    """
    symbol_upper = symbol.upper()
    current_time = datetime.datetime.now(datetime.timezone.utc)
    current_date = current_time.date()
    r = 0.06 # 6% risk-free rate proxy

    chain_data = nse_client.get_multi_expiry_mock_data(symbol_upper)
    source = chain_data.get("source", "simulated-multi-expiry")
    note = chain_data.get("note", "Multi-expiry data simulated due to NSE live API access restrictions (403) on this deployment; single-expiry IV smile above uses real/near-real data.")

    records = chain_data.get("records", {})
    underlying_value = records.get("underlyingValue") or 0.0
    raw_data = records.get("data", [])

    surface_points = []
    raw_points_count = 0
    filtered_points_count = 0

    for item in raw_data:
        strike_price = item.get("strikePrice")
        expiry_date_str = item.get("expiryDate")
        if not strike_price or not expiry_date_str:
            continue

        try:
            expiry_dt = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        except Exception:
            try:
                expiry_dt = datetime.date.fromisoformat(expiry_date_str)
            except Exception:
                expiry_dt = current_date

        days_to_expiry = max((expiry_dt - current_date).days, 1)
        T = days_to_expiry / 365.0

        for option_side in ("CE", "PE"):
            opt_data = item.get(option_side)
            if not opt_data:
                continue

            raw_points_count += 1
            ltp = opt_data.get("lastPrice") or 0.0
            oi = opt_data.get("openInterest") or 0
            nse_iv = opt_data.get("impliedVolatility") or 0.0

            # Compute IV using original tested iv_solver
            solved_iv = 0.0
            if ltp > 0 and underlying_value > 0 and strike_price > 0:
                try:
                    solved_vol = implied_volatility(
                        ltp, underlying_value, strike_price, T, r,
                        'call' if option_side == "CE" else 'put'
                    )
                    solved_iv = solved_vol * 100.0
                except Exception:
                    solved_iv = nse_iv if nse_iv > 0 else 0.0

            # Filter thresholds: OI >= 50, LTP >= 1.0, 3.0% <= IV <= 150.0%
            if oi >= 50 and ltp >= 1.0 and (3.0 <= solved_iv <= 150.0):
                filtered_points_count += 1
                surface_points.append({
                    "strike": float(strike_price),
                    "expiry_date": expiry_date_str,
                    "days_to_expiry": int(days_to_expiry),
                    "option_side": option_side,
                    "ltp": float(ltp),
                    "oi": int(oi),
                    "computed_iv": round(solved_iv, 2),
                    "nse_iv": round(nse_iv, 2)
                })

    # Summary analysis for dynamic interpretation note
    expiries_list = sorted(list(set(pt["expiry_date"] for pt in surface_points)))
    strikes_list = sorted(list(set(pt["strike"] for pt in surface_points)))

    return {
        "symbol": symbol_upper,
        "underlying_value": underlying_value,
        "fetched_at": current_time.isoformat(),
        "source": source,
        "note": note,
        "filter_criteria": {
            "min_open_interest": 50,
            "min_ltp": 1.0,
            "min_iv_pct": 3.0,
            "max_iv_pct": 150.0
        },
        "raw_points_count": raw_points_count,
        "filtered_points_count": filtered_points_count,
        "distinct_expiries_count": len(expiries_list),
        "distinct_strikes_count": len(strikes_list),
        "expiries": expiries_list,
        "points": surface_points
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
    
    # d_sigma_raw is the change in volatility as a raw decimal (e.g. 0.0108
    # for a move from 7.86% to 8.94%). vega_val is expressed per 1
    # PERCENTAGE POINT of IV change (industry convention, see core/greeks.py),
    # so we convert d_sigma to percentage points (multiply by 100) before
    # multiplying, to keep both sides of this multiplication in the same units.
    d_sigma_raw = (req.current_volatility - req.volatility) if req.current_volatility is not None else 0.0
    d_sigma_percentage_points = d_sigma_raw * 100
    vega_pnl = vega_val * d_sigma_percentage_points * req.quantity * sign

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
