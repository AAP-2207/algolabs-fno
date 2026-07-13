const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface GreekDetail {
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  computed_iv: number;
  nse_iv: number;
  ltp: number;
}

export interface GreekStrikeRecord {
  strike: number;
  CE: GreekDetail | null;
  PE: GreekDetail | null;
}

export interface GreeksResponse {
  fetched_at: string;
  source: "live-polled" | "mock";
  age_minutes: number;
  strikes: GreekStrikeRecord[];
}

/**
 * Fetches option chain Greeks & IV from the backend API.
 */
export async function fetchGreeks(symbol: string = "NIFTY"): Promise<GreeksResponse> {
  const response = await fetch(`${API_BASE_URL}/api/greeks?symbol=${symbol}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch greeks: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
