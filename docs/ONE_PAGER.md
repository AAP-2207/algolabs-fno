# Project One-Pager Report — AlgoLabs F&O

## 1. What Was Implemented

AlgoLabs F&O was built to deliver a complete derivatives analytics suite and trade-lifecycle strategy engine:
- **Option Chain Desk (`/chain`)**: Interactive NIFTY 50 option chain with LTP, OI, Volume, Implied Volatility (IV), Put-Call Ratio (PCR) sentiment analysis, Max Pain calculation, and freshness timestamp badges.
- **Greeks & Implied Volatility Desk (`/greeks`)**: Black-Scholes-Merton (BSM) risk Greeks ($\Delta, \Gamma, \Theta, \text{Vega}$) computed using SciPy, BSM-computed IV vs NSE reported IV comparison, 2D IV smile visualization, and a 3D Volatility Surface across strikes and expiry dates (with simulated multi-expiry data clearly labeled).
- **P&L Greek Decomposer Desk (`/pnl`)**: First-order Taylor series risk attribution ($\Delta, \Gamma, \Theta, \text{Vega}$, residual) with an explicit user warning when residual error exceeds 15% of net P&L.
- **DOS Strategy Panel & Backtester (`/dos`)**: TradingView-validated SuperTrend 5-minute signal panel, Wed/Thu gating logic, automated strike recommendations, stop-loss monitor (50% Wed / 100% Thu initial SL, trailing SL), and an 8-week historical backtester (Jan–Feb 2024, 16 trade days, 100% completion).

---

## 2. How It Was Implemented

- **Quantitative Core (Python, SciPy, NumPy)**: Options pricing and Greeks use standard BSM formulations. Implied Volatility is solved using SciPy's Brent's method (`scipy.optimize.brentq`) for exact root-finding. P&L decomposition uses first-order Taylor series expansion anchored to entry state.
- **SuperTrend Validation**: Wilder's Smoothing ATR and SuperTrend bands were validated line-by-line against TradingView's Pine Script calculations (`period=10, multiplier=3`).
- **Web Application Stack**: FastAPI backend serving structured JSON endpoints to a Vite + React 18 TypeScript frontend styled with TailwindCSS and shadcn/ui.

---

## 3. Key Design Decisions & Architecture Rationale

- **Senior-Approved Local-Poller Architecture**: Direct cloud requests to NSE from Render return `403 Forbidden` due to Akamai bot detection. Instead of incurring monthly proxy costs or resorting to fragile TLS-spoofing hacks, a local poller running on a residential IP writes option chain snapshots to Supabase. The deployed backend reads the latest snapshot from Supabase.
- **Current Operating Mode**: To avoid residential IP rate-flagging under aggressive 5-minute polling, the local poller is currently paused. When Supabase snapshots are unpolled or >60m old, the backend gracefully serves BSM mock fallbacks anchored to live Yahoo Finance spot prices.
- **100% Data Transparency**: Every endpoint and screen includes `source` (`live-polled` vs `mock`), `fetched_at` timestamp, and `age_minutes` so staleness is always visible, never concealed.

---

## 4. What Would Be Improved With More Time

1. **WebSockets Integration**: Transition from HTTP polling to WebSockets for sub-second streaming option chain ticks.
2. **Live Multi-Expiry Feed**: Ingest live multi-expiry option chain feeds across all upcoming weekly/monthly cycles to replace the simulated multi-expiry feed on the 3D volatility surface.
3. **Automated Poller Failover & Safe Resumption**: Implement automated proxy rotation for the poller and resume background ingestion at a safe, rate-limit-friendly interval (e.g. 15 minutes).
4. **Intraday Granularity Backtester**: Ingest intraday 5-minute options tick data to model intraday trailing stop-losses in historical backtests.

