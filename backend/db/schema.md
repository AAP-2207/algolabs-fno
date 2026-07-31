# Database Schema Notes

This document tracks the SQL schemas utilized by the F&O Derivatives Analytics Platform.

## 1. Option Chain Snapshots (`option_chain_snapshots`)

Stores NIFTY option chain snapshots polled from NSE.

## 2. DOS Trades (`dos_trades`)

Stores option trades executed or simulated by the Daily Option Seller (DOS) strategy engine.

### SQL Schema Definition

To create the `dos_trades` table in Supabase, execute the following SQL query in the Supabase SQL Editor:

```sql
create table dos_trades (
  id uuid default gen_random_uuid() primary key,
  trade_date date,
  day_type text, -- e.g., 'Normal', 'Expiry', etc.
  option_type text, -- 'CE' or 'PE'
  strike numeric, -- Strike price of the option traded
  entry_time timestamptz, -- UTC entry timestamp
  entry_premium numeric, -- Price at entry
  exit_time timestamptz, -- UTC exit timestamp
  exit_premium numeric, -- Price at exit
  exit_reason text, -- e.g., 'Target', 'StopLoss', 'EOD', etc.
  pnl numeric, -- Profit / Loss (exit_premium - entry_premium for shorts, or vice-versa)
  is_backtest boolean default false, -- True if simulated, False if live
  created_at timestamptz default now()
);
```

## 3. Bhavcopy Options Cache (`bhavcopy_cache`)

Caches filtered BANKNIFTY option contracts fetched from NSE. This avoids hitting `nsearchives.nseindia.com` live from cloud environments (e.g. Render) where egress is blocked.

### SQL Schema Definition

To create the `bhavcopy_cache` table in Supabase, execute the following SQL query in the Supabase SQL Editor:

```sql
create table bhavcopy_cache (
  trade_date date primary key,
  data jsonb not null,
  created_at timestamptz default now()
);
```
