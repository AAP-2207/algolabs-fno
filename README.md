# AlgoLabs F&O Derivatives Analytics Platform + DOS Strategy

A derivatives analytics platform and DOS strategy engine for Futures & Options trading.

## Overview
AlgoLabs F&O is an options analytics and strategy execution platform that provides live derivatives analytics (option chain, Greeks, implied volatility) and implements the Direction of SuperTrend (DOS) intraday options strategy. It includes a built-in P&L decomposer for options positions, a TradingView-validated SuperTrend engine, a live-monitoring strategy panel with automatic trade lifecycle management, and a historical backtesting engine using NSE Bhavcopy files.

## Features

### Option Chain
- **Option Chain Display**: Renders real-time option chain data including Strike Price, Expiry, CE/PE Bid/Ask, Last Price, Implied Volatility (IV), and Open Interest (OI).
- **Greeks Calculation**: Real-time pricing and risk sensitivity metrics—Delta, Gamma, Theta, and Vega—calculated dynamically via a Black-Scholes-Merton (BSM) engine.
- **Dynamic IV & Spot Anchoring**: Solves for implied volatility from option prices and anchors option chains to Yahoo Finance-fetched spot prices with realistic mock data fallbacks.

### P&L Decomposer
- **Greeks Attribution**: Decomposes option position P&L into individual risk factors including Delta P&L (spot price moves), Gamma P&L (second-order spot moves), Theta P&L (time decay), and Vega P&L (implied volatility changes).

### SuperTrend Indicator
- **TradingView-Validated Engine**: Implementation of the Wilders Average True Range (ATR) and SuperTrend indicator, fully validated against TradingView outputs.
- **Trend Signals**: Generates bullish/bearish signals to guide option buying strategy.

### DOS Strategy Live Panel
- **Intraday Signal Tracking**: Monitored on a 5-minute candle basis, showing the live SuperTrend state, current option contracts, and selected strikes.
- **Automatic Trade Lifecycle**: Manages position entries, monitors trailing stop-loss or initial stop-loss targets, and manages automatic daily trade termination at market close (3:30 PM).

### Backtester
- **Historical Replay Engine**: Backtests the DOS strategy at daily granularity using NSE Bhavcopy ZIP files.
- **Comprehensive P&L Analysis**: Simulates trades over specified date ranges and provides detailed metrics on win rate, total P&L, and trade journals.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, Vite, TypeScript, TailwindCSS, shadcn/ui, Recharts |
| **Backend** | Python, FastAPI, Uvicorn |
| **Database** | Supabase, PostgreSQL |
| **Math & Science** | NumPy, SciPy, Pandas |
| **Data Sources** | Yahoo Finance (`yfinance`), NSE Bhavcopy (ZIP EOD files), Direct NSE Option Chain API with realistic BSM-based Mock Fallback |

---

## Architecture

The platform uses a hybrid architecture designed to serve fresh data while gracefully handling exchange rate limits and blocks.

```
+------------------+     (Pushes raw JSON)     +-------------------+
|   Local Poller   | ------------------------> | Supabase Database |
+------------------+                           +-------------------+
                                                         |
                                                         | (Reads snapshot)
                                                         v
+------------------+     (HTTP JSON Request)   +-------------------+
|  Web Frontend    | <------------------------ |  FastAPI Backend  |
+------------------+                           +-------------------+
                                                         | (Direct Live Fetch)
                                                         | or (BSM Mock Fallback)
                                                         v
                                               +-------------------+
                                               |   NSE India API   |
                                               +-------------------+
```

- **Live Flow**: A local poller retrieves live option chain data from the NSE website and stores snapshots in Supabase. The FastAPI backend queries the latest snapshot from Supabase, serving it to the frontend with age and freshness metadata.
- **Mock-Fallback Path**: If no snapshot is available in Supabase, or if a direct API call to NSE is made and fails due to bot-detection rate limits, the backend automatically falls back to generating realistic mock option chains. These chains are calculated using the BSM pricing model, anchored to live underlying spot prices via `yfinance`, with simulated tick fluctuation and realistic open-interest bell curves.

---

### Screen Breakdown

1. **Option Chain (`/chain`)**: Interactive real-time option chain table for Nifty with strike prices, LTP, OI, IV, Put-Call Ratio (PCR) commentary card, Max Pain commentary card, and freshness badge (`fetched_at`, `age_minutes`).
2. **Greeks & Pricing (`/greeks`)**: Displays all 4 Black-Scholes Greeks (Delta, Gamma, Theta, Vega) per strike, computed IV vs NSE IV, and a 2D IV smile curve chart across strikes for the active expiry.
3. **P&L Decomposer (`/pnl`)**: Interactive form allowing custom position entry (strike, CE/PE, buy/sell, quantity, price, spot move, elapsed time, IV shift) with a waterfall chart decomposing total P&L into Delta, Gamma, Theta, Vega, and residual contributions.
4. **DOS Strategy Panel (`/dos`)**: Live SuperTrend 5-minute indicator chart, active/inactive gating banner (Wednesday & Thursday > 9:20 AM IST), strike auto-selector with full Greeks + IV, initial and trailing stop-loss visual monitor, 4-week historical backtester UI, and automated plain-language trade cards.

---

## Setup Instructions

### Environment Variables
Create a `.env` file in the `backend/` directory and `frontend/` directory using the provided `.env.example` templates.

**Backend (`backend/.env`)**:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
NSE_API_BASE_URL=https://www.nseindia.com
PORT=8000
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Frontend (`frontend/.env`)**:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Steps to Run

1. **Clone the Repository**
   ```bash
   git clone https://github.com/armando/algolabs-fno.git
   cd algolabs-fno
   ```

2. **Setup Backend**
   Navigate to the backend directory, create a virtual environment, install dependencies, and run the FastAPI server:
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

3. **Setup Frontend**
   Navigate to the frontend directory, install dependencies, and start the development server:
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

4. **Setup Local Poller (Optional - for Live NSE Data Ingestion)**
   To populate Supabase with live option chain snapshots from a local residential IP:
   ```bash
   cd backend
   python scripts/poller.py
   # Or set up as a scheduled task / cron job running every 1-5 minutes
   ```

---

## Known Limitations

This section documents deliberate scope decisions and real infrastructure constraints discovered during development — included here in the interest of transparency, not as an afterthought.

### Live NSE Option Chain Data

**Status: Sourced via local residential IP poller writing to Supabase; falls back to realistic mock data if unpolled. Direct live fetch from cloud IPs (Render) is blocked by NSE's Akamai bot protection.**

During development, the live NSE option-chain API (`www.nseindia.com`) was found to be blocked at the network/transport layer by NSE's Akamai-based bot protection — confirmed through direct testing, not assumed:

- Requests using Python's `requests` library returned `403 Forbidden` consistently, across multiple distinct cloud networks (Render, GitHub Actions), ruling out a simple IP-based rate limit.
- A direct browser visit or residential IP request to the same URL loaded successfully — confirming the block is specific to datacenter/cloud IP ranges and automated non-browser TLS handshakes.
- **Engineering decision:** a local residential IP poller writes fresh snapshots to Supabase `option_chain_snapshots`. The deployed backend reads the latest snapshot from Supabase, returning honest timestamps (`fetched_at`, `age_minutes`, `source`) to the user.

### 2D Volatility Smile vs 3D Volatility Surface

The platform renders a 2D IV smile curve across strike prices for the single active expiry (as explicitly allowed by the assignment specification fallback), rather than a multi-expiry 3D volatility surface.

### Bank Nifty Weekly Options — Discontinued Nov 2024

The DOS (Direction of SuperTrend) strategy in this project is built around Bank Nifty **weekly** options, per the original assignment brief. During development, it was discovered that SEBI directed NSE to limit weekly index options to one benchmark per exchange, effective **November 20, 2024** — NSE retained Nifty 50 weekly options and discontinued Bank Nifty weekly options entirely.

This means:
- The **backtester** is unaffected — it uses historical data from when Bank Nifty weekly options were active (Wednesday expiry: Sept 2023–Nov 2024; Thursday expiry: May 2016–Sept 2023), which is a normal and expected use of historical backtesting.
- The **live DOS panel** demonstrates the strategy's logic and structure faithfully to the original spec, but the specific instrument (Bank Nifty weekly options) is no longer tradeable on the live exchange today. This is a fact about current market structure, not a bug in the implementation.

### Backtester: Daily Granularity, Not Intraday

NSE's Bhav Copy (the only free historical options data source) publishes **end-of-day** data only — no free historical intraday option premium data exists. As a result:

- The backtester operates at **daily granularity**. SuperTrend is computed on daily Bank Nifty candles (not 5-minute, as the live panel uses), since `yfinance` retains years of daily history but only ~60 days of 5-minute data.
- Entry price is approximated as the option's opening price that day (falling back to closing price for illiquid contracts with no opening trade).
- Initial stop-loss detection uses the day's High price — if it breached the SL level, the trade is assumed to exit exactly at the SL price (the standard, honest convention for daily-bar backtesting, since the exact intraday fill price isn't knowable from EOD data alone).
- **Trailing stop-loss is not modeled in the backtester.** Detecting it requires knowing whether the underlying crossed the SuperTrend line *within* a trading day — information daily bars cannot provide. Only the initial SL and market-close exit conditions are simulated historically. This is a deliberate, documented scope decision, not an oversight.

### Sample Size

The 4-week backtest sample (the assignment's minimum requirement) happened to show a uniformly bearish (PE-only) signal across all four weeks tested. This satisfies the specified minimum but does not demonstrate a CE-side trade, and four weeks is too small a sample to draw statistically meaningful conclusions about the strategy's real edge — it demonstrates the mechanism working correctly, not a validated trading edge.

---

## Testing

The project has a comprehensive automated test suite consisting of **77** unit and integration tests.
To run the test suite:
```bash
cd backend
.venv\Scripts\python -m pytest tests/ -v
```

The test coverage spans:
- **Mathematical Core**: Validation of Black-Scholes pricing options formula (`core/bsm.py`) and Greek values (Delta, Gamma, Theta, Vega via Brent's method IV solver).
- **SuperTrend Validation**: Verifies ATR (Wilder's RMA) and indicator generation logic matches TradingView expectations.
- **Trade Lifecycle**: Evaluates trade entry signals, stop-loss calculations (50% Wed / 100% Thu), trailing stop-losses, and market-close exits.
- **Bhavcopy Parsing**: Confirms schema structures, zip extractions, and data validation rules for NSE Bhavcopy.
- **Backtester Logic**: Validates that historical daily replays execute, accumulate P&L metrics, and catch potential data anomalies without lookahead bias.
- **API Endpoints**: Validates `/health`, `/api/option-chain`, `/api/greeks`, `/api/pnl-decompose`, `/api/dos/signal`, `/api/dos/backtest`, and `/api/dos/trades`.

