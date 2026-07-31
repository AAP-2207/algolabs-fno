# AlgoLabs F&O Derivatives Analytics Platform + DOS Strategy Engine

A full-stack options analytics platform and automated trading signal/backtesting engine for Nifty and Bank Nifty Futures & Options (F&O) derivatives, built as part of the SoFI Core Induction Assignment 2 (Project 2).

> **Before submitting**: confirm the live Vercel URL you're sharing loads cleanly with no browser console errors — the backend's CORS configuration was recently updated to handle Vercel preview-deployment URLs, and this must be re-verified against the actual deployed link (not just localhost) after the latest deploy completes.

---

## 1. Overview

AlgoLabs F&O gives a trader a single dashboard to understand Nifty options pricing, risk, and sentiment, and to run a specific rules-based options-selling strategy — DOS (Direction of SuperTrend) on Bank Nifty weekly expiries — both live and against historical data. It combines a live(ish) option chain, a Black-Scholes-Merton Greeks/IV engine, a P&L attribution tool, and an automated signal + backtesting engine for the DOS strategy, all built on a React frontend and a FastAPI backend backed by Supabase.

This is a decision-support and analytics tool, **not** an auto-trading system — it never places real orders. It tells a trader what the data means and what the DOS strategy would recommend; a human still pulls the trigger on their own broker terminal.

---

## 2. Architecture & Data Flow

```
+-------------------+      (Pushes raw JSON)      +-------------------+
|  Local Poller     | --------------------------> | Supabase Database |
| (Residential IP)  |                              +-------------------+
+-------------------+                                       |
  [Currently Paused]                                        | (Reads latest snapshot)
                                                              v
+-------------------+      (HTTPS JSON Request)    +-------------------+
|   Vercel Web       | <--------------------------- |  Render FastAPI   |
|     Frontend       |                               |      Backend      |
+-------------------+                               +-------------------+
                                                              | (Falls back to fresh
                                                              |  BSM-priced mock data
                                                              |  if no recent snapshot)
                                                              v
                                                    +-------------------+
                                                    |  NSE India / Yahoo |
                                                    |  Finance / Bhavcopy|
                                                    +-------------------+
```

### Why this architecture — the NSE data ingestion journey

1. **Direct cloud fetch attempt.** The backend first tried fetching the NSE option chain directly from `www.nseindia.com` on every request. This worked from a local machine but failed consistently from cloud infrastructure (Render, and separately GitHub Actions) with `403 Forbidden` — NSE's Akamai-based bot detection blocks known datacenter IP ranges and inspects TLS fingerprints.
2. **Local poller solution.** Rather than pay for a rotating residential proxy service, a small poller script runs on a local residential-IP machine, fetches the live NSE option chain, and writes JSON snapshots into Supabase on a schedule.
3. **Current operating state.** After polling aggressively every 5 minutes, the residential IP began showing signs of rate-flagging from NSE, so the poller has been paused as a precaution. When Supabase has no snapshot fresher than 60 minutes (or the snapshot has fewer than 3 strikes, indicating a bad/partial write), the backend automatically falls back to internally generated, BSM-priced mock data centered on a live Yahoo Finance spot price — so the app never crashes or silently shows stale numbers as if they were live.
4. **Full transparency, always.** Every data-carrying API response and every corresponding UI screen displays explicit freshness metadata: `fetched_at`, `age_minutes`, and `source` (`"live-polled"` vs `"mock"`). The system never claims to be real-time when it isn't.

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, Recharts, Lucide Icons |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| Database | Supabase (PostgreSQL) |
| Math / Quant | NumPy, SciPy (`scipy.optimize.brentq` for the IV solver), Pandas |
| Data Sources | NSE Live Option Chain API (with BSM mock fallback), NSE EOD Bhavcopy (ZIP/CSV), `yfinance` (spot price & historical OHLCV) |
| Hosting | Vercel (frontend), Render (backend), Supabase (managed Postgres) |

---

## 4. Screens & Features

### `/chain` — Option Chain Desk
Live-style Nifty option chain: strikes, CE/PE Last Traded Price, Open Interest, Change in OI, Volume, and per-strike Implied Volatility. Above the table: spot price ticker, a Put-Call Ratio card with a plain-language sentiment read (bullish/bearish/neutral), a Max Pain strike card, and a freshness badge showing exactly how old the displayed data is and whether it's live-polled or mock fallback.

### `/greeks` — Greeks & Implied Volatility Desk
For every strike in the current chain: Delta, Gamma, Theta, and Vega for both CE and PE, computed via the Black-Scholes-Merton model. A separate "Computed IV" column shows the volatility solved via Brent's method against each option's actual traded price — distinct from the raw NSE-quoted IV shown on `/chain`, and labeled as such so the two numbers aren't mistaken for a discrepancy. Below the table, a 2D Implied Volatility smile plots CE and PE IV across strikes, with a plain-language card interpreting whether current IV levels look elevated, normal, or suppressed relative to a baseline.

### `/pnl` — P&L Greek Decomposer Desk
A position builder (option type, buy/sell, strike, quantity, entry/current premium, previous/current spot, days elapsed, entry/current IV) that decomposes the position's P&L into a first-order Taylor expansion: Delta P&L + Gamma P&L + Theta P&L + Vega P&L + a residual term, visualized as a waterfall chart, with a plain-language summary of which Greek drove the move. If the residual exceeds roughly 15% of total P&L — which can happen for large, multi-day position shifts where a first-order approximation naturally loses accuracy — the UI surfaces an explicit warning rather than silently presenting a misleading breakdown.

### `/dos` — DOS Strategy Panel & Backtester
Implements the Direction of SuperTrend strategy on Bank Nifty Futures exactly as specified:

- **Instrument & timeframe**: Bank Nifty Futures, 5-minute candles.
- **Active days**: Wednesday and Thursday only (expiry days); any other day shows an explicit "inactive" banner, never an error or blank screen.
- **SuperTrend parameters**: period 10, multiplier 3.
- **Entry gating**: no new entry signal before 9:20 AM IST.
- **Signal logic**: BNF Futures price above SuperTrend → sell CE. Price below SuperTrend → sell PE.
- **Strike selection**: nearest 100 rounded from the current SuperTrend value (not spot price).
- **Initial stop-loss**: 50% of premium sold on Wednesday, 100% on Thursday, applied as day-type-conditional multipliers.
- **Trailing stop-loss**: triggers when price closes above whichever of the CE-side or PE-side SuperTrend value is lower.
- **Default exit**: market close (3:30 PM IST) if neither stop-loss is hit.

On screen: a live SuperTrend signal panel with trend direction and a candle countdown, a strike auto-selector showing the recommended CE/PE strike with its LTP, IV, and all four Greeks, a stop-loss monitor visualizing both the initial and trailing SL levels against the live premium, and a historical backtester covering 8 weekly expiry days (Wednesdays + Thursdays) using NSE EOD Bhavcopy data, reporting win rate, average P&L, SL hit rate, a full equity curve, and a per-trade log. Every completed trade — live or backtested — gets an auto-generated plain-language interpretation card, and the full trade log is persisted to Supabase with entry, exit, and P&L attribution split explicitly by day type (Wednesday vs Thursday).

---

## 5. Setup Instructions

### Environment variables

**`backend/.env`**
```env
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
PORT=8000
ALLOWED_ORIGINS=https://your-production-domain.vercel.app,http://localhost:3000,http://localhost:5173
```

**`frontend/.env`**
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SHOW_DEV_CONTROLS=false
```

### Running locally

```bash
git clone https://github.com/AAP-2207/algolabs-fno.git
cd algolabs-fno
```

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd ../frontend
npm install
npm run dev -- --port 3000
```

**Local residential poller** (optional, only needed to refresh live Supabase snapshots):
```bash
cd backend
python scripts/poller.py
```
For unattended background execution on Windows, schedule `python.exe backend/scripts/poller.py` via Task Scheduler to run every 5–15 minutes during NSE market hours (9:15 AM – 3:30 PM IST).

---

## 6. Known Limitations & Engineering Transparency

1. **NSE cloud IP blocking, poller currently paused.** Direct NSE requests from cloud IP ranges (Render, GitHub Actions) return `403 Forbidden` via Akamai bot detection. Live data is sourced through a local residential-IP poller writing to Supabase; the poller is currently paused after aggressive polling triggered rate-flagging. When no fresh Supabase snapshot exists, the app transitions to BSM-priced mock data with an explicit `source: "mock"` badge — it never presents fallback data as if it were live. Additionally, a real, authentic NSE snapshot was manually captured via an authenticated browser session and inserted to demonstrate the full live-data pipeline working end-to-end with genuine market data, alongside the automated poller architecture (which remains the primary mechanism, currently paused after being rate-flagged).
2. **Polling, not WebSockets.** Market data updates via scheduled HTTP polling rather than a persistent WebSocket stream.
3. **3D Volatility surface implemented with simulated multi-expiry data.** A 3D volatility surface (Strikes x Expiry Dates x Implied Volatility) is implemented directly below the untouched 2D IV smile on `/greeks`. The multi-expiry data it uses is simulated rather than live, because NSE blocks live multi-expiry option chain requests from this deployment (403, same Akamai restriction documented elsewhere in this README) and no multi-expiry historical data snapshot was available within the project timeline. The surface's skew and term structure follow realistic, documented patterns rather than random noise, and this is clearly labeled with a prominent warning badge in the UI itself.
4. **Backtester uses EOD Bhavcopy granularity.** Entry prices are approximated from opening prints and initial SL checks use daily high prints; true intraday tick-by-tick execution (which the trailing SL rule conceptually depends on for maximal precision) is not simulated. The backtester follows the same rule logic as the live signal engine, but at daily-bar resolution.
5. **Backtest expiry-date calculation fix.** An earlier bug hardcoded `expiry_date` equal to `trade_date` for every backtest day, causing many days (particularly Thursdays, which expire on the following Wednesday under the current weekly cycle) to fail with "no matching Bhavcopy rows." This was fixed by computing the actual applicable weekly expiry date per trading day rather than assuming same-day expiry, which increased backtest day coverage substantially. **This specific fix has not been independently re-verified with a fresh full backtest run as of this README's writing — recommend re-running the 8-week backtest and confirming the reported success/failure counts before treating this as fully resolved.**
6. **First-order Taylor expansion limits.** Large position/spot moves over multi-day windows can produce a meaningfully large residual term in the P&L decomposer, since a first-order approximation loses accuracy as the move size grows. The UI surfaces an explicit warning when residual exceeds ~15% of total P&L rather than hiding this limitation.
7. **Developer gating bypass hidden in production.** A "Gating Bypass" toggle exists to let developers test the DOS panel outside Wednesday/Thursday market hours; it is conditionally hidden in production builds via `VITE_SHOW_DEV_CONTROLS=false`.
8. **CORS / deployment URL sensitivity.** The backend's allowed-origins configuration handles Vercel preview-deployment subdomains dynamically using a CORS regex pattern (`https://algolabs-.*\.vercel\.app`) in `CORSMiddleware`. This automatically matches all unique preview hash subdomains generated for project deployments, while keeping static entries for localhost and the promoted production URL. If `ALLOWED_ORIGINS` is set in the Render environment variables, it serves as the explicit allowed origins list, but standard Vercel subdomains are supported out-of-the-box.
9. **F&O Bhavcopy cloud IP blocking.** Live F&O Bhavcopy zip downloads from `nsearchives.nseindia.com` get blocked with a `403 Forbidden` from Render's cloud IP (same Akamai restriction as the live option chain). To solve this, we implemented a Supabase-based cache table `bhavcopy_cache` that stores the parsed and filtered `BANKNIFTY` options data. The backend checks this cache first before making a live HTTP request to NSE. A local backfill script (`backend/scripts/backfill_bhavcopy.py`) was executed from a residential IP to pre-seed this cache for all weekly expiries in the backtest range (Jan-Feb 2024), guaranteeing 100% successful backtests in production without hitting NSE.

---


## 7. Assignment Requirements Cross-Reference

| Requirement (from assignment spec) | Status | Where |
|---|---|---|
| Live NSE option chain — OI, LTP, IV per strike | Done | `/chain` |
| Greeks (Delta, Gamma, Theta, Vega) via Black-Scholes for all strikes | Done | `/greeks` |
| IV solver via reverse BSM with Brent's method | Done | `backend/core/iv_solver.py` |
| Volatility surface (3D across strikes & expiries) | Done (3D surface implemented; multi-expiry data simulated, clearly labeled - see Known Limitations #3) | `/greeks` |

| P&L Decomposer (Delta/Gamma/Theta/Vega attribution) | Done | `/pnl` |
| Interpretation cards — PCR, Max Pain, IV spike | Done | `/chain`, `/greeks` |
| DOS: live SuperTrend panel, Wed/Thu only | Done | `/dos` |
| DOS: strike auto-selector with LTP, IV, Greeks | Done | `/dos` |
| DOS: SL monitor, initial + trailing | Done | `/dos` |
| DOS: backtester — win rate, avg P&L, SL hit rate, equity curve, per-trade | Done | `/dos` |
| DOS: trade log in Supabase, P&L split by day type | Done | `dos_trades` table |
| DOS: interpretation card per trade | Done | `/dos` |
| GitHub repo, clean commits, README | Done | this repository |
| Working full-stack app, deployed | Pending final live verification — see note at top of this README | Vercel + Render |
| One-pager report | Done | `docs/ONE_PAGER.md` |

---

## 8. Automated Testing

```bash
cd backend
.venv\Scripts\python -m pytest tests/ -v
```

Test coverage includes: BSM pricing and Greeks correctness, the Brent's-method IV solver, SuperTrend calculation validated against TradingView reference values, P&L decomposer accuracy and residual-threshold behavior, backtester expiry-date logic (pre- and post-September-2023 Bank Nifty expiry-day conventions), the DOS trailing-SL "whichever ST value is lower" rule specifically, backtest date-generation deduplication, and integration tests across every API endpoint (`/health`, `/api/option-chain`, `/api/greeks`, `/api/pnl-decompose`, `/api/dos/signal`, `/api/dos/backtest`, `/api/dos/trades`).
