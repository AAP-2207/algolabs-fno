const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  supertrend: number;
  trend: "up" | "down" | string;
}

export interface OpenTradeData {
  strike: number;
  option_side: string;
  entry_premium: number;
  entry_time: string;
  day_type: "wednesday" | "thursday" | string;
  current_premium: number | null;
  initial_sl_price: number;
  unrealized_pnl: number | null;
}

export interface DosSignalResponse {
  active: boolean;
  reason?: string;
  timestamp: string;
  close?: number;
  supertrend_value?: number;
  trend?: string;
  option_side?: string;
  recommended_strike?: number;
  just_flipped?: boolean;
  strike_data_available?: boolean;
  ltp?: number | null;
  iv?: number | null;
  delta?: number | null;
  gamma?: number | null;
  theta?: number | null;
  vega?: number | null;
  candles?: CandleData[];
  open_trade?: OpenTradeData | null;
}

/**
 * Fetches DOS signal data from the backend API.
 */
export async function fetchDosSignal(bypassGating?: boolean): Promise<DosSignalResponse> {
  const url = bypassGating
    ? `${API_BASE_URL}/api/dos/signal?bypass_gating=true`
    : `${API_BASE_URL}/api/dos/signal`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch DOS signal: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Backtest types
// ---------------------------------------------------------------------------

export interface EquityPoint {
  trade_date: string;
  cumulative_pnl: number;
}

export interface BacktestTrade {
  trade_date: string;
  day_type: string;
  option_side: string;
  strike: number;
  entry_price: number;
  exit_price: number;
  exit_reason: string;
  pnl: number;
}

export interface BacktestError {
  trade_date: string;
  error: string;
}

export interface BacktestSummary {
  total_trades_attempted: number;
  successful_trades: number;
  failed_trades: number;
  win_rate_pct: number | null;
  avg_pnl: number | null;
  total_pnl: number;
  initial_sl_hit_rate_pct: number | null;
  equity_curve: EquityPoint[];
  trades: BacktestTrade[];
  errors: BacktestError[];
}

export async function runBacktest(
  startDate: string = "2024-02-07",
  weeks: number = 4
): Promise<BacktestSummary> {
  const response = await fetch(`${API_BASE_URL}/api/dos/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start_date: startDate, weeks }),
  });
  if (!response.ok) {
    throw new Error(`Backtest failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

