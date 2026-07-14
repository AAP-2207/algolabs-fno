import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Cpu, AlertTriangle, RefreshCw } from "lucide-react";
import { fetchDosSignal } from "../api/dos";
import type { DosSignalResponse } from "../api/dos";
import { SuperTrendSignalPanel } from "../components/dos/SuperTrendChart";
import { StopLossMonitor } from "../components/dos/StopLossMonitor";

export const DosPage: React.FC = () => {
  const [data, setData] = useState<DosSignalResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isFetching, setIsFetching] = useState<boolean>(false);
  const [bypassGating, setBypassGating] = useState<boolean>(false);

  useEffect(() => {
    let active = true;

    const loadSignal = async () => {
      setIsFetching(true);
      try {
        const res = await fetchDosSignal(bypassGating);
        if (active) {
          setData(res);
          setError(null);
        }
      } catch (err: any) {
        console.error(err);
        if (active) {
          setError("Failed to fetch live DOS signal data.");
        }
      } finally {
        if (active) {
          setLoading(false);
          setIsFetching(false);
        }
      }
    };

    loadSignal();

    // Poll every 5 seconds
    const interval = setInterval(loadSignal, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [bypassGating]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-zinc-950 text-zinc-100 p-8">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-400" />
          <span className="text-sm font-semibold tracking-wide font-mono text-zinc-400">Loading DOS Strategy Engine...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-zinc-950 text-zinc-100 p-8 overflow-y-auto">
      <div className="max-w-6xl w-full mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-3">
            <Cpu className="h-6 w-6 text-indigo-400 animate-pulse" />
            <h2 className="text-xl font-bold tracking-tight text-zinc-100">DOS Strategy Engine</h2>
          </div>
          
          <div className="flex items-center gap-6">
            {/* Simulation Bypass Switch - Only visible in DEV mode */}
            {import.meta.env.DEV && (
              <div className="flex items-center gap-3 bg-zinc-900/50 border border-zinc-850 rounded-xl px-4 py-2 shadow-inner">
                <span className="text-xs font-semibold font-mono tracking-wide text-zinc-400">Gating Bypass</span>
                <button
                  id="gating-bypass-toggle"
                  onClick={() => setBypassGating(!bypassGating)}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    bypassGating ? "bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" : "bg-zinc-700"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      bypassGating ? "translate-x-4" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            )}

            {isFetching && (
              <div className="flex items-center gap-2 text-zinc-500 text-xs font-mono">
                <RefreshCw className="h-3 w-3 animate-spin text-zinc-400" />
                <span>fetching...</span>
              </div>
            )}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Data Stream Connection Issue</p>
              <p className="text-xs text-red-400/80">{error}</p>
            </div>
          </div>
        )}

        {/* Inactive Banner */}
        {data && !data.active && (
          <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 p-6 rounded-2xl space-y-3">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="h-6 w-6 shrink-0" />
              <h3 className="font-bold text-lg">DOS Strategy Inactive</h3>
            </div>
            <p className="text-sm text-zinc-300 font-medium">
              {data.reason || "The Daily Option Seller (DOS) strategy is currently inactive."}
            </p>
            <div className="bg-zinc-950/50 p-4 rounded-xl border border-zinc-800 text-xs text-zinc-500 font-mono">
              <span>Gating details: Wednesday and Thursday starting at 9:20 AM IST or later.</span>
            </div>
          </div>
        )}

        {/* Active Strategy Dashboard */}
        {data && data.active && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left/Middle Columns: Chart & Info */}
            <div className="lg:col-span-2 space-y-6">
              <SuperTrendSignalPanel
                candleData={data.candles || []}
                currentTrend={data.trend || "down"}
                lastUpdated={data.timestamp}
              />

              {/* Metrics Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Card className="bg-zinc-900/30 border-zinc-800 backdrop-blur-sm shadow-xl">
                  <CardHeader className="pb-2">
                    <span className="text-xs text-zinc-400 uppercase tracking-wider font-mono">Spot Price</span>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold text-zinc-100 font-mono">
                      ₹{data.close ? data.close.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "--"}
                    </p>
                    <span className="text-xs text-zinc-500">Bank Nifty Index Spot</span>
                  </CardContent>
                </Card>

                <Card className="bg-zinc-900/30 border-zinc-800 backdrop-blur-sm shadow-xl">
                  <CardHeader className="pb-2">
                    <span className="text-xs text-zinc-400 uppercase tracking-wider font-mono">SuperTrend Value</span>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold text-zinc-100 font-mono">
                      ₹{data.supertrend_value ? data.supertrend_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "--"}
                    </p>
                    <span className="text-xs text-zinc-500">Indicator value (period=10, multiplier=3)</span>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Right Column: Execution Recommendations & Option Details */}
            <div className="space-y-6">
              {data.open_trade && (() => {
                const isBreached = (data.open_trade.current_premium ?? 0) >= data.open_trade.initial_sl_price;
                const breachReason = isBreached ? "initial" : null;
                return (
                  <StopLossMonitor
                    entryPremium={data.open_trade.entry_premium}
                    currentPremium={data.open_trade.current_premium ?? 0}
                    initialSlLevel={data.open_trade.initial_sl_price}
                    trailingSlLevel={null}
                    dayType={data.open_trade.day_type as "wednesday" | "thursday"}
                    isBreached={isBreached}
                    breachReason={breachReason}
                    /* 
                       TODO/FOLLOW-UP: The lotSize is currently hardcoded on the frontend. 
                       Ideally, the backend endpoint GET /api/dos/signal should return the lot_size 
                       directly (referencing BANKNIFTY_LOT_SIZE = 30 from core/trade_lifecycle.py)
                       to serve as a single source of truth across the stack.
                    */
                    lotSize={30}
                  />
                );
              })()}

              <Card className="bg-gradient-to-b from-indigo-950/20 to-zinc-900/30 border-zinc-800 shadow-2xl backdrop-blur-sm h-full flex flex-col">
                <CardHeader className="border-b border-zinc-800/50 pb-4">
                  <CardTitle className="text-sm font-semibold uppercase tracking-wider text-indigo-400 font-mono flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    Execution Engine
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 flex-1 flex flex-col justify-between space-y-6">
                  {/* Strategy recommendation card */}
                  <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-5 space-y-3">
                    <div className="text-xs text-zinc-500 uppercase tracking-wider font-mono">Recommended Order</div>
                    <div className="flex items-baseline gap-2">
                      <span className={`text-2xl font-extrabold tracking-tight ${data.option_side === "CE" ? "text-green-400" : "text-red-400"}`}>
                        SELL {data.recommended_strike} {data.option_side}
                      </span>
                    </div>
                    {data.just_flipped && (
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        Trend Flipped this candle
                      </div>
                    )}
                  </div>

                  {/* Options Data Availability Alert */}
                  {!data.strike_data_available && (
                    <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 flex items-start gap-2.5">
                      <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                      <div className="text-xs text-amber-300/90 leading-relaxed">
                        <span className="font-semibold block text-amber-400">Greeks unavailable</span>
                        The option chain doesn't contain strikes matching the current SuperTrend level. Using fallback values.
                      </div>
                    </div>
                  )}

                  {/* Option Premium / LTP */}
                  <div className="space-y-4">
                    <div className="flex justify-between items-center border-b border-zinc-800/60 pb-3">
                      <span className="text-sm text-zinc-400 font-medium">Estimated Premium (LTP)</span>
                      <span className="text-xl font-bold font-mono text-zinc-100">
                        {data.ltp !== null && data.ltp !== undefined ? `₹${data.ltp.toFixed(2)}` : "--"}
                      </span>
                    </div>

                    {/* Greeks Details Grid */}
                    <div className="grid grid-cols-2 gap-3.5">
                      <div className="bg-zinc-900/40 p-3 rounded-xl border border-zinc-800/40">
                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-mono block mb-1">Delta (Δ)</span>
                        <span className="text-sm font-semibold font-mono text-zinc-200">
                          {data.delta !== null && data.delta !== undefined ? data.delta.toFixed(4) : "--"}
                        </span>
                      </div>
                      <div className="bg-zinc-900/40 p-3 rounded-xl border border-zinc-800/40">
                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-mono block mb-1">Gamma (Γ)</span>
                        <span className="text-sm font-semibold font-mono text-zinc-200">
                          {data.gamma !== null && data.gamma !== undefined ? data.gamma.toFixed(6) : "--"}
                        </span>
                      </div>
                      <div className="bg-zinc-900/40 p-3 rounded-xl border border-zinc-800/40">
                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-mono block mb-1">Theta (Θ)</span>
                        <span className="text-sm font-semibold font-mono text-zinc-200">
                          {data.theta !== null && data.theta !== undefined ? data.theta.toFixed(2) : "--"}
                        </span>
                      </div>
                      <div className="bg-zinc-900/40 p-3 rounded-xl border border-zinc-800/40">
                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-mono block mb-1">Vega (ν)</span>
                        <span className="text-sm font-semibold font-mono text-zinc-200">
                          {data.vega !== null && data.vega !== undefined ? data.vega.toFixed(2) : "--"}
                        </span>
                      </div>
                    </div>

                    <div className="flex justify-between items-center bg-zinc-900/20 px-4 py-3 rounded-xl border border-zinc-800/40 mt-2">
                      <span className="text-xs text-zinc-400 font-medium font-mono">Implied Volatility</span>
                      <span className="text-sm font-semibold font-mono text-indigo-400">
                        {data.iv !== null && data.iv !== undefined ? `${data.iv.toFixed(2)}%` : "--"}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DosPage;
