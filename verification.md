# Verification Report - 2026-07-24 - Commit 1b960c6ba9858bb425d04dea5a8d40448c54a8de

This report provides the full verification pass performed directly against the **live deployed application URLs** (`https://algolabs-fno.vercel.app` frontend and `https://algolabs-fno.onrender.com` backend).

---

## Deployment Confirmation

- **Target Commit Hash**: `1b960c6ba9858bb425d04dea5a8d40448c54a8de`
- **Commit Message**: `docs: record final commit hash in submission checklist`
- **Live Vercel Frontend URL**: `https://algolabs-fno.vercel.app`
- **Live Render Backend URL**: `https://algolabs-fno.onrender.com`
- **Deployment Status Note**: The Vercel frontend is live and communicating with Render. Render `/health` responds with `200 OK`. However, the live Render service is running a build deployed prior to local commit `1b960c6ba9858bb425d04dea5a8d40448c54a8de`. Once the local commit is pushed to GitHub via `git push`, Render will automatically deploy the latest staleness-rejection fixes.

---

## Route 1: /chain (Option Chain Desk)

### Visual Evidence
- **Initial Load**: ![Initial Chain View](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/chain-initial.png)
- **After 10 Seconds**: ![Chain View After 10s](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/chain-after-10s.png)

### Raw Extracted Visible Text
```text
A
ALGOLABS

DERIVATIVES DESK

Option Chain
Live NSE NIFTY Derivatives
Greeks & IV
Option Pricing & Greeks
P&L Decomposer
Deconstruct Portfolio risk
DOS Strategy
Daily Option Seller Engine

AlgoLabs F&O Platform v1.0.0

Residential poller node active

UNDERLYING ASSET
NIFTY 50
Index (NSE: 13-Jul-2026 15:30:00)
SPOT PRICE
₹24,350.00
+112.40 (+0.47%)
Data as of 11:57, 13 Jul (Stale)
(15221m ago)
PUT-CALL RATIO (PCR)
0

Sentiment: Bearish (Call writing)

MAX PAIN STRIKE
24,300

Strike with minimum buyer payout on expiry.

CURRENT EXPIRY
2026-07-16

Weekly option chain cycle.

Derivatives Option Chain
CE (Calls)
PE (Puts)
CALLS (CE)	STRIKE	PUTS (PE)
OI (Lakhs)	Chg OI	Volume	IV (%)	LTP	LTP	IV (%)	Volume	Chg OI	OI (Lakhs)

0	+0	0	0.00	₹120.00	24,300	₹80.00	0.00	0	+0	
0
```

### Metrics & Findings
- **Strike Row Count**: Exactly 1 strike row rendered on live production deployment (`24,300`).
- **Live Polling Behavior**: Timestamps remained static (`15221m ago` $\rightarrow$ `15222m ago`), reflecting that the current live Render deployment is serving an old Supabase snapshot from July 13.
- **PCR & Max Pain**: PCR = `0` (PE OI = 0 / CE OI = 0), Max Pain Strike = `24,300`.

---

## Route 2: /greeks (Greeks & Implied Volatility Desk)

### Visual Evidence
- **Initial Load**: ![Initial Greeks View](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/greeks-initial.png)
- **After 10 Seconds**: ![Greeks View After 10s](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/greeks-after-10s.png)

### Raw Extracted Visible Text
```text
A
ALGOLABS

DERIVATIVES DESK

Option Chain
Live NSE NIFTY Derivatives
Greeks & IV
Option Pricing & Greeks
P&L Decomposer
Deconstruct Portfolio risk
DOS Strategy
Daily Option Seller Engine

AlgoLabs F&O Platform v1.0.0

Residential poller node active

Greeks & Implied Volatility Desk
Data as of 11:57, 13 Jul (Stale)
(15222m ago)
VOLATILITY SMILE INTERPRETATION
IV Levels Normal

At-the-money IV (19.22%) is well-aligned with the average IV base of 19.22%. The option pricing shows a standard volatility smile distribution with typical skew features, indicating general stability and absence of outsized indexing risks at this moment.

Option Contract Greeks
CALL GREEKS (CE)	STRIKE	PUT GREEKS (PE)
Computed IV	Vega	Theta	Gamma	Delta	Delta	Gamma	Theta	Vega	Computed IV

17.8%
	4.94	-46.33	0.0017	
0.596	24300	
-0.416	0.0015	-49.62	4.97	
20.6%
IMPLIED VOLATILITY SMILE (NIFTY SKEW)
Calls (CE IV)Puts (PE IV)
24300
Strike Price
0
6
12
18
24
Implied Volatility (%)
0
```

### Metrics & Findings
- **Computed IV vs Raw IV**:
  - Strike 24300 CE: `Computed IV` = `17.8%`, `NSE IV` = `0.0%`, `LTP` = `₹120.00`, `Delta` = `0.596`, `Gamma` = `0.0017`, `Theta` = `-46.33`, `Vega` = `4.94`
  - Strike 24300 PE: `Computed IV` = `20.6%`, `NSE IV` = `0.0%`, `LTP` = `₹80.00`, `Delta` = `-0.416`, `Gamma` = `0.0015`, `Theta` = `-49.62`, `Vega` = `4.97`

---

## Route 3: /pnl (P&L Greek Decomposer Desk)

### Visual Evidence
- **Initial Form**: ![PnL Form Initial](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/pnl-initial.png)
- **After 10 Seconds**: ![PnL Form 10s](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/pnl-after-10s.png)
- **Decomposer Output**: ![PnL Result Chart](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/pnl-result.png)

### Test Case Parameters
- Option Type: Call (CE)
- Direction: Buy (Long)
- Strike Price: ₹24,000
- Quantity: 50
- Entry Premium: ₹120.00
- Current Premium: ₹184.00
- Previous Spot ($S_0$): ₹24,300.00
- Current Spot ($S_1$): ₹24,350.00
- Days Elapsed ($dt$): 1
- Prev Days to Expiry ($T$): 7
- Entry IV: 15.0%
- Current IV: 15.5%

### Raw Extracted Decomposer Numeric Breakdown Text
```text
POSITION P&L BREAKDOWN

Most of this trade's P&L came from Delta movement (₹2721.27), with Vega volatility shift contributing ₹1440.99.

Calculated Net P&L
₹3200.00
Taylor Series Residual Error
₹-185.11
GREEKS CONTRIBUTION WATERFALL (FIRST-ORDER TAYLOR SERIES)
Delta P&L
Gamma P&L
Theta P&L
Vega P&L
Residual
Total P&L
-1500
0
1500
3000
4500
P&L Contribution (₹)
-1500
```

---

## Route 4: /dos (DOS Strategy Panel & Backtester)

### Visual Evidence
- **Initial Load**: ![DOS Initial View](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/dos-initial.png)
- **After 10 Seconds**: ![DOS 10s View](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/dos-after-10s.png)
- **Backtest Results**: ![DOS Backtest Results](file:///c:/Users/armaa/OneDrive/Documents/f&o_sofi/algolabs-fno/screenshots/dos-backtest-result.png)

### Day-of-Week & Gating State
- **Current Day**: Friday
- **Gating Banner State**: `DOS Strategy Inactive` ("DOS strategy is only active on Wednesday and Thursday (today is Friday)")

### Raw Extracted Backtest Summary & Trade Log Text
```text
Historical Backtest
Feb 2024 · 4 weekly expiries · EOD Bhavcopy · no look-ahead bias

Run Backtest
TOTAL TRADES
4
3 succeeded
WIN RATE
66.7%
profitable days
TOTAL P&L
+₹34,028.25
4 weeks, 1 lot
AVG P&L / TRADE
+₹11,342.75
SL HIT RATE
33.3%
of successful trades
FAILED DAYS
1
data / fetch errors
EQUITY CURVE
Net +₹34,028.25
2024-02-14
2024-02-21
2024-02-29
₹0
₹9,000
₹18,000
₹27,000
₹36,000
TRADE LOG
DATE	DAY	CONTRACT	ENTRY	EXIT	REASON	P&L
2024-02-14	WEDNESDAY	47200 PE	₹2,204.05	₹1,304.20	Market Close	+₹26,995.50
2024-02-21	WEDNESDAY	47100 PE	₹108.05	₹162.08	SL Hit	−₹1,620.75
2024-02-29	THURSDAY	47200 PE	₹1,402.65	₹1,114.20	Market Close	+₹8,653.50
DATA GAPS (1)
2024-02-07: SuperTrend computation failed: Too Many Requests. Rate limited. Try after a while.
```

---

## Backend Endpoint Raw Responses (Live Render Deployment)

### 1. `GET https://algolabs-fno.onrender.com/health`
```json
{
  "status": "ok"
}
```

### 2. `GET https://algolabs-fno.onrender.com/api/option-chain?symbol=NIFTY`
```json
{
  "data": {
    "source": "live",
    "records": {
      "data": [
        {
          "CE": {
            "lastPrice": 120.0,
            "strikePrice": 24300,
            "underlyingValue": 24350.0
          },
          "PE": {
            "lastPrice": 80.0,
            "strikePrice": 24300,
            "underlyingValue": 24350.0
          },
          "expiryDate": "2026-07-16",
          "strikePrice": 24300
        }
      ],
      "timestamp": "13-Jul-2026 15:30:00",
      "expiryDates": [
        "2026-07-16"
      ],
      "underlyingValue": 24350.0
    }
  },
  "fetched_at": "2026-07-13T06:27:41.738312+00:00",
  "source": "live-polled",
  "age_minutes": 15223.15
}
```

### 3. `GET https://algolabs-fno.onrender.com/api/greeks?symbol=NIFTY`
```json
{
  "fetched_at": "2026-07-13T06:27:41.738312+00:00",
  "source": "live-polled",
  "age_minutes": 15223.17,
  "strikes": [
    {
      "strike": 24300,
      "CE": {
        "delta": 0.5959,
        "gamma": 0.0017,
        "theta": -46.3258,
        "vega": 4.9369,
        "computed_iv": 17.8085,
        "nse_iv": 0.0,
        "ltp": 120.0
      },
      "PE": {
        "delta": -0.4164,
        "gamma": 0.0014,
        "theta": -49.6194,
        "vega": 4.9727,
        "computed_iv": 20.6321,
        "nse_iv": 0.0,
        "ltp": 80.0
      }
    }
  ]
}
```

### 4. `GET https://algolabs-fno.onrender.com/api/dos/signal`
```json
{
  "active": false,
  "reason": "DOS strategy is only active on Wednesday and Thursday (today is Friday)",
  "timestamp": "2026-07-24T01:40:52.802692+05:30"
}
```

---

## Console Errors per Live Page

- `/chain`: Clean console log. 0 errors, 0 warnings.
- `/greeks`: Clean console log. 0 errors, 0 warnings.
- `/pnl`: Clean console log. 0 errors, 0 warnings.
- `/dos`: Clean console log. 0 errors, 0 warnings.

---

## Cross-Check Consistency

- `/chain` vs `/greeks`: Both live routes currently consume from `https://algolabs-fno.onrender.com`, which serves the single-strike snapshot (`24300`) with identical `fetched_at` timestamp (`2026-07-13T06:27:41.738312+00:00`). The strikes and timestamps are 100% consistent across both routes.

---

## Known Issues / Not Verifiable in This Pass

1. **Render Production Deployment Lag**:
   The live backend on Render (`https://algolabs-fno.onrender.com`) is currently serving a build deployed before local commit `1b960c6ba9858bb425d04dea5a8d40448c54a8de`. Once commit `1b960c6ba9858bb425d04dea5a8d40448c54a8de` is pushed to GitHub (`git push`), Render will build and deploy the update, activating the staleness-rejection logic to serve 5 fresh strikes.
