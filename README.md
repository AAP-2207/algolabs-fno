# AlgoLabs F&O Derivatives Analytics Platform + DOS Strategy Engine

A full-stack options analytics platform and automated trading engine for Futures & Options (F&O) derivatives.

## Overview
AlgoLabs F&O provides real-time options analytics including an interactive Option Chain desk, Black-Scholes-Merton (BSM) Greeks, and dynamic Implied Volatility (IV) smile visualization. It features a Taylor-series P&L Decomposer for portfolio risk attribution, a TradingView-validated SuperTrend engine, a Direction of SuperTrend (DOS) live panel with automated trade lifecycle management, and an 8-week historical backtester powered by NSE EOD Bhavcopy data.

---

## Architecture & Data Flow

```
+-------------------+      (Pushes raw JSON)      +-------------------+
|  Local Poller     | --------------------------> | Supabase Database |
| (Residential IP)  |                             +-------------------+
+-------------------+                                       |
  [Currently Paused]                                        | (Reads snapshot)
                                                            v
+-------------------+      (HTTP JSON Request)    +-------------------+
|   Vercel Web      | <-------------------------- |  Render FastAPI   |
|     Frontend      |                             |      Backend      |
+-------------------+                             +-------------------+
                                                            | (Fresh BSM Mock
                                                            |  Fallback if unpolled)
                                                            v
                                                  +-------------------+
                                                  |   NSE India API   |
                                                  +-------------------+
```

### Engineering Rationale: The NSE Data Ingestion Journey
1. **Direct Cloud Fetch Attempt**: Initially, the backend attempted to fetch option chains directly from `www.nseindia.com`. While this worked on local machines, it failed consistently on cloud infrastructure (Render, GitHub Actions) with `403 Forbidden` due to NSE's Akamai-based datacenter IP blocks and TLS fingerprinting.
2. **Local Poller Solution**: To bypass cloud IP blocks without recurring paid proxy costs, a local poller script was built to run on a residential IP and write fresh JSON snapshots into Supabase.
3. **Current Operating State**: Following aggressive 5-minute polling, the local poller script was paused to prevent residential IP rate-flagging. In accordance with senior-approved architectural guidelines, when Supabase snapshots are missing or older than 60 minutes, the backend seamlessly transitions to a BSM-calculated mock fallback centered around live Yahoo Finance spot prices.
4. **Complete Transparency**: Every API response and UI screen displays explicit freshness metadata (`fetched_at`, `age_minutes`, `source`), ensuring stale or fallback data is never disguised as live exchange feeds.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, TypeScript, TailwindCSS, Lucide Icons, Recharts |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| **Database** | Supabase (PostgreSQL) |
| **Math & Quantitative** | NumPy, SciPy (Brent's method BSM IV solver), Pandas |
| **Data Sources** | Yahoo Finance (`yfinance`), NSE EOD Bhavcopy (ZIP), NSE Live Option Chain API (with BSM Mock Fallback) |

---

## Screen & Feature Breakdown

1. **Option Chain Desk (`/chain`)**: Live NIFTY 50 option chain displaying strikes, LTP, Open Interest (OI), Volume, Implied Volatility (IV), Put-Call Ratio (PCR) with market sentiment analysis, Max Pain calculation, and freshness status badge.
2. **Greeks & IV Desk (`/greeks`)**: Computes option contract Greeks ($\Delta, \Gamma, \Theta, \text{Vega}$) using SciPy's BSM pricing model, compares BSM computed IV against NSE reported IV, and renders a 2D Implied Volatility smile chart across active strikes.
3. **P&L Greek Decomposer Desk (`/pnl`)**: Deconstructs custom position P&L into first-order Taylor series risk attributions ($\Delta, \Gamma, \Theta, \text{Vega}$, and residual error). Includes an explicit mathematical accuracy warning when Taylor expansion residual error exceeds 15% of net P&L.
4. **DOS Strategy Panel & Backtester (`/dos`)**: Live 5-minute SuperTrend indicator panel, market day gating (Wed/Thu > 9:20 AM IST), automated strike recommendation, stop-loss monitor (50% Wed / 100% Thu initial SL, trailing SL), and an 8-week historical backtester (Jan–Feb 2024, 16 trade days, 100% completion).

---

## Setup Instructions

### Environment Configuration
Create a `.env` file in `backend/` and `frontend/`:

**Backend (`backend/.env`)**:
```env
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
PORT=8000
ALLOWED_ORIGINS=https://algolabs-fno.vercel.app,http://localhost:3000,http://localhost:5173
```

**Frontend (`frontend/.env`)**:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SHOW_DEV_CONTROLS=false
```

### Running Locally

1. **Clone the Repository**
   ```bash
   git clone https://github.com/AAP-2207/algolabs-fno.git
   cd algolabs-fno
   ```

2. **Start Backend Server**
   ```bash
   cd backend
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

3. **Start Frontend Server**
   ```bash
   cd ../frontend
   npm install
   npm run dev -- --port 3000
   ```

4. **Local Residential Poller Setup (Task Scheduler / Cron)**
   To run the local poller script to write fresh NSE snapshots to Supabase:
   ```bash
   cd backend
   python scripts/poller.py
   ```
   *For automated background execution on Windows:* Set up Windows Task Scheduler to trigger `python.exe backend/scripts/poller.py` every 5–15 minutes during market hours (9:15 AM - 3:30 PM IST).

---

## Known Limitations & Engineering Transparency

1. **Cloud IP Blocks & Paused Poller**: Direct requests from cloud IP ranges (Render, GitHub Actions) to NSE are blocked by Akamai bot detection (`403 Forbidden`). Sourcing relies on a local residential IP poller writing to Supabase. The local poller is currently **paused** after aggressive 5-minute polling triggered IP rate-flagging. The application gracefully transitions to BSM mock fallbacks with explicit timestamp badges (`age_minutes: 0.0`, `source: mock`).
2. **Polling Updates vs WebSockets**: Market updates use HTTP polling intervals rather than WebSocket streams.
3. **2D Volatility Smile vs 3D Volatility Surface**: Renders a single-expiry 2D IV smile across strikes (permitted under assignment fallback options) rather than a full multi-expiry 3D volatility surface.
4. **EOD Bhavcopy Backtester Granularity**: Backtesting uses daily NSE Bhavcopy files. Entry prices are approximated as opening prints, initial SL uses daily high prints, and trailing SL (which requires intraday tick sequence data) is not simulated.
5. **Backtest Expiry Date Calculation Fix**: During verification, a bug was identified where `expiry_date` was hardcoded equal to `trade_date`, causing Thursday backtest trade attempts to fail due to missing Bhavcopy rows (since Thursday options expire on the following Wednesday). Fix: Implemented dynamic weekly expiry date calculation (`get_weekly_expiry_date`), expanding successful backtest trade execution from 8/16 days (50%) to **16/16 days (100%)**.
6. **First-Order Taylor Expansion Limitations**: Large position shifts (e.g., 800-point spot moves over 14 days) produce significant higher-order residual error. The P&L Decomposer UI explicitly alerts users when residual error exceeds 15% of net P&L.
7. **Production Gating Bypass Control**: A "Gating Bypass" toggle exists for local developer testing outside Wednesday/Thursday market hours. It is conditionally hidden in production builds via `VITE_SHOW_DEV_CONTROLS`.

---

## Automated Testing

The project maintains an automated unit and integration test suite (**82 passed tests**):

```bash
cd backend
.venv\Scripts\python -m pytest tests/ -v
```

### Test Coverage Highlights
- **BSM & Greeks Engine**: Tests option pricing, delta/gamma/theta/vega values, and Brent's method IV solver (`test_bsm.py`, `test_greeks.py`, `test_iv_solver.py`).
- **SuperTrend Validation**: Verifies ATR Wilders smoothing and trend direction against TradingView targets (`test_supertrend.py`).
- **P&L Decomposer & Residual Thresholds**: Tests first-order Taylor expansion accuracy and residual threshold behavior for large moves (`test_pnl_decompose.py`).
- **Backtester Expiry Calculation**: Tests historical Thursday (pre-Sep 2023) and Wednesday (post-Sep 2023) expiry date logic (`test_expiry_calc.py`, `test_backtester.py`).
- **API Endpoints**: Integration tests for `/health`, `/api/option-chain`, `/api/greeks`, `/api/pnl-decompose`, `/api/dos/signal`, and `/api/dos/backtest` (`test_dos.py`, `test_greeks_endpoint.py`, `test_market_data.py`).
