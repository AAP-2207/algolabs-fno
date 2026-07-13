import type { OptionChainResponse } from "../mockData";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Fetches option chain data for a given symbol from the backend API.
 */
export async function fetchOptionChain(symbol: string = "NIFTY"): Promise<OptionChainResponse> {
  const response = await fetch(`${API_BASE_URL}/api/option-chain?symbol=${symbol}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch option chain: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
