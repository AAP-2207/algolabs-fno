# Project One-Pager Report

## What Was Implemented

AlgoLabs F&O was built to deliver derivatives analytics and trade-lifecycle simulation through several integrated modules. The platform features an Option Chain system that processes live and mock market data to compute options prices, implied volatility (IV), and Black-Scholes-Merton risk Greeks (Delta, Gamma, Theta, Vega) in real-time. Position risk is evaluated through a dedicated P&L Decomposer, which breaks down option position returns into Delta, Gamma, Theta, and Vega attribution components. Technical analysis is handled by an ATR-based SuperTrend indicator engine, which was verified line-by-line against TradingView's mathematical output. The live trading loop is simulated in the DOS Strategy Panel, allowing users to select ATM/OTM strikes, track intraday buy signals, monitor trailing stop-losses, and execute automated end-of-day exits. Finally, a historical backtesting engine ingests daily NSE Bhavcopy files, runs the strategy through a historical window, and outputs comprehensive performance metrics and trade journals.

---

## How It Was Implemented

Several key design decisions guided the implementation of the platform:

- **FastAPI + React/Vite**: FastAPI was chosen for the backend due to its asynchronous support, speed, automatic OpenAPI generation, and compatibility with scientific Python libraries (Pandas, SciPy, NumPy) required for option Greeks calculations. React with Vite and TypeScript was chosen for the frontend to enable a responsive UI that handles real-time updates efficiently.
- **v0 & shadcn/ui Components**: We used v0 and shadcn/ui components to build a dashboard using clean visual representations, polished chart libraries (Recharts), and responsive layouts, avoiding clunky table interfaces.
- **Polling vs. WebSockets**: Since index option chains and yfinance spot feeds updated at fixed intervals (seconds/minutes) rather than high-frequency microsecond ticks, a client-initiated polling strategy (5-second intervals) was implemented. This avoided the overhead, connection state management, and complexity of WebSockets while remaining within the limits of the public data providers.
- **Supabase Database**: Supabase was selected to provide a PostgreSQL database with a simple client interface, allowing the application to persist historical backtest outputs, database schemas, and option chain snapshots easily.
- **Local-Poller Pattern for Live Data**: To address exchange rate-limiting and connection blocks, a separate poller script was decoupled from the main request-response thread. The poller aggregates the live option-chain snapshot, writes it to Supabase, and the FastAPI application queries the database snapshot, protecting the user-facing web server from latency spikes or request timeouts.

---

## Data Architecture — Investigation & Decision Process

### The Problem

Early in development, the live NSE option-chain API returned `403 Forbidden` when called from the deployed backend (Render). The obvious first hypothesis — a simple cloud-IP block — was tested and ruled out through a structured investigation, not assumed:

1. **Direct fetch from Render** → `403 Forbidden`
2. **Direct fetch from an alternate cloud provider (GitHub Actions)** → same `403`, ruling out Render specifically and pointing to datacenter IP ranges broadly
3. **Fetch from a local residential IP** → succeeded once, confirming residential IPs were treated differently
4. **Repeated automated polling from that same residential IP** → eventually also blocked, indicating behavior-based (not purely IP-based) detection
5. **A second, unrelated residential network (mobile hotspot)** → blocked immediately, on the very first request, with zero prior history — ruling out "this specific IP has a bad reputation" as a complete explanation
6. **A real browser, on that same blocked network, at the same time** → loaded NSE successfully

That last test was decisive: it proved the block wasn't about network, IP reputation, or rate limits at all. It was specific to how NSE's Akamai-based bot protection fingerprints automated HTTP clients (Python's `requests` library, and even headless browser automation) differently from a genuine browser — at the TLS handshake and HTTP/2 connection layer, before any application-level headers are even evaluated.

### The Decision

At this point, a further technical path existed: TLS/browser-fingerprint impersonation (via libraries like `curl_cffi`, which deliberately mimic a real browser's exact TLS ClientHello to defeat this class of bot detection). This was evaluated and **deliberately not pursued** — not because it wouldn't likely work, but because it crosses a meaningful line from "building a resilient client" to "actively defeating a security system a company maintains for a reason." That's a judgment call about where legitimate engineering ends, and it was made deliberately rather than defaulted into.

### The Architecture That Was Built Instead

- Every live data fetch attempts the real API first.
- On failure, the system falls back to **realistic simulated data** — computed using the same validated Black-Scholes pricing engine used everywhere else in the platform, anchored to a real, live spot price from an unaffected data source (`yfinance`), with realistic tick movement and open-interest distribution.
- Every API response is explicitly labeled with its data source (`live` or `mock`) and a freshness timestamp — nothing is silently faked or hidden.
- Historical data (Bhav Copy) and spot/candle data (`yfinance`) — both used by the backtester and the SuperTrend engine — come from different NSE infrastructure entirely and were confirmed unaffected by this issue throughout development.

### Why This Matters

This same investigative discipline — verify before trusting, test the actual mechanism rather than the first plausible theory, hand-check real numbers instead of assuming a passing test means correctness — was applied throughout the project, and caught several genuine bugs before they could reach the final build: a false-positive indicator signal during a warm-up period, a stale mock spot price disconnected from real market levels, a mispriced mock options formula, an industry-standard unit-convention error in the Greeks engine, a look-ahead bias in the backtester's signal timing, and a leap-year date-calculation edge case. Each was caught by testing the actual behavior against real data rather than trusting that code which ran without errors was necessarily correct.

---

## What I'd Improve With More Time

1. **Intraday Backtesting & Trailing SL**: Expand the backtesting engine's capabilities by modeling trailing stop-losses, which requires 1-minute or 5-minute tick data for the underlying index.
2. **Larger Backtest Windows**: Extend the historical backtesting sample size past the initial 4-week window to run over multiple years of index options data, confirming the strategy's real edge under varying market regimes.
3. **Configurable Strategy Instrument**: Allow the user to configure which instrument to run on the live strategy panel, specifically adding support for Nifty 50 weekly options (which remain active) to make the live panel tradeable under current SEBI regulations.
4. **CI/CD Integration**: Add automated GitHub Actions pipelines to run pytest across branches and environment platforms to prevent regression in pricing and lifecycle modules.
