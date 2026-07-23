import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  CartesianGrid,
} from "recharts";
import { TrendingUp, HelpCircle, AlertCircle, ArrowRightLeft } from "lucide-react";

interface PnlDecomposeResponse {
  total_pnl: number;
  delta_pnl: number;
  gamma_pnl: number;
  theta_pnl: number;
  vega_pnl: number;
  residual: number;
  summary: string;
}

export const PnlPage: React.FC = () => {
  // Pre-filled realistic default parameters
  const [strike, setStrike] = useState<number>(24300);
  const [optionType, setOptionType] = useState<"CE" | "PE">("CE");
  const [position, setPosition] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState<number>(100);
  const [entryPrice, setEntryPrice] = useState<number>(120.0);
  const [currentPrice, setCurrentPrice] = useState<number>(152.0);
  
  const [previousS, setPreviousS] = useState<number>(24300.0);
  const [currentS, setCurrentS] = useState<number>(24350.0);
  const [daysElapsed, setDaysElapsed] = useState<number>(1.0);
  const [volatility, setVolatility] = useState<number>(7.86); // as percentage
  const [currentVolatility, setCurrentVolatility] = useState<number>(8.94); // as percentage
  const [daysToExpiry, setDaysToExpiry] = useState<number>(7.0);

  const [result, setResult] = useState<PnlDecomposeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleDecompose = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    try {
      const response = await fetch(`${API_BASE_URL}/api/pnl-decompose`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          strike,
          option_type: optionType,
          position,
          quantity,
          entry_price: entryPrice,
          current_price: currentPrice,
          current_S: currentS,
          previous_S: previousS,
          days_elapsed: daysElapsed,
          volatility: volatility / 100.0, // Convert to decimal for backend
          days_to_expiry: daysToExpiry,
          current_volatility: currentVolatility / 100.0, // Convert to decimal for backend
        }),
      });

      if (!response.ok) {
        throw new Error(`Calculation failed: ${response.statusText}`);
      }

      const data: PnlDecomposeResponse = await response.json();
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to decompose P&L");
    } finally {
      setLoading(false);
    }
  };

  // Chart dataset mapper
  const chartData = result
    ? [
        { name: "Delta P&L", value: Number(result.delta_pnl.toFixed(2)) },
        { name: "Gamma P&L", value: Number(result.gamma_pnl.toFixed(2)) },
        { name: "Theta P&L", value: Number(result.theta_pnl.toFixed(2)) },
        { name: "Vega P&L", value: Number(result.vega_pnl.toFixed(2)) },
        { name: "Residual", value: Number(result.residual.toFixed(2)) },
        { name: "Total P&L", value: Number(result.total_pnl.toFixed(2)) },
      ]
    : [];

  return (
    <div className="flex-1 flex flex-col bg-zinc-950 text-zinc-100 overflow-y-auto">
      {/* HEADER */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-zinc-950/85 border-b border-zinc-800/80 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ArrowRightLeft className="h-5 w-5 text-emerald-500" />
          <h2 className="font-bold text-lg text-zinc-100">P&L Greek Decomposer Desk</h2>
        </div>
      </header>

      {/* CONTAINER */}
      <main className="p-8 space-y-8 flex-1 max-w-7xl w-full mx-auto">
        <form onSubmit={handleDecompose} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* POSITION BUILDER CARD */}
          <Card className="bg-zinc-900/30 border-zinc-850 shadow-lg">
            <CardHeader>
              <CardTitle className="text-zinc-200 text-sm font-semibold uppercase tracking-wider">
                1. Position Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Option Type Toggle */}
              <div>
                <Label className="text-zinc-400 text-xs">Option Type</Label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  <button
                    type="button"
                    onClick={() => setOptionType("CE")}
                    className={`py-2 text-xs font-semibold rounded-lg border transition-all ${
                      optionType === "CE"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/50"
                        : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    Call (CE)
                  </button>
                  <button
                    type="button"
                    onClick={() => setOptionType("PE")}
                    className={`py-2 text-xs font-semibold rounded-lg border transition-all ${
                      optionType === "PE"
                        ? "bg-rose-500/10 text-rose-400 border-rose-500/50"
                        : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    Put (PE)
                  </button>
                </div>
              </div>

              {/* Position Direction Toggle */}
              <div>
                <Label className="text-zinc-400 text-xs">Direction</Label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  <button
                    type="button"
                    onClick={() => setPosition("buy")}
                    className={`py-2 text-xs font-semibold rounded-lg border transition-all ${
                      position === "buy"
                        ? "bg-blue-500/10 text-blue-400 border-blue-500/50"
                        : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    Buy (Long)
                  </button>
                  <button
                    type="button"
                    onClick={() => setPosition("sell")}
                    className={`py-2 text-xs font-semibold rounded-lg border transition-all ${
                      position === "sell"
                        ? "bg-purple-500/10 text-purple-400 border-purple-500/50"
                        : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    Sell (Short)
                  </button>
                </div>
              </div>

              {/* Strike Price */}
              <div>
                <Label className="text-zinc-400 text-xs" htmlFor="strike">
                  Strike Price
                </Label>
                <Input
                  id="strike"
                  type="number"
                  value={strike}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStrike(Number(e.target.value))}
                  className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                />
              </div>

              {/* Position Quantity */}
              <div>
                <Label className="text-zinc-400 text-xs" htmlFor="quantity">
                  Contracts Quantity
                </Label>
                <Input
                  id="quantity"
                  type="number"
                  value={quantity}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuantity(Number(e.target.value))}
                  className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                />
              </div>

              {/* Entry & Current Premium Prices */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="entryPrice">
                    Entry Premium
                  </Label>
                  <Input
                    id="entryPrice"
                    type="number"
                    step="0.05"
                    value={entryPrice}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEntryPrice(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="currentPrice">
                    Current Premium
                  </Label>
                  <Input
                    id="currentPrice"
                    type="number"
                    step="0.05"
                    value={currentPrice}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentPrice(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* SIMULATION SLIDERS CARD */}
          <Card className="bg-zinc-900/30 border-zinc-850 shadow-lg">
            <CardHeader>
              <CardTitle className="text-zinc-200 text-sm font-semibold uppercase tracking-wider">
                2. Market Simulation
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Previous & Current Spot Prices */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="previousS">
                    Previous Spot Price (S₀)
                  </Label>
                  <Input
                    id="previousS"
                    type="number"
                    value={previousS}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPreviousS(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="currentS">
                    Current Spot Price (S₁)
                  </Label>
                  <Input
                    id="currentS"
                    type="number"
                    value={currentS}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentS(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
              </div>

              {/* Time Parameters */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="daysElapsed">
                    Days Elapsed (dt)
                  </Label>
                  <Input
                    id="daysElapsed"
                    type="number"
                    step="0.1"
                    value={daysElapsed}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDaysElapsed(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="daysToExpiry">
                    Prev Days to Expiry (T)
                  </Label>
                  <Input
                    id="daysToExpiry"
                    type="number"
                    value={daysToExpiry}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDaysToExpiry(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
              </div>

              {/* Volatility Parameters */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="volatility">
                    Entry IV (%)
                  </Label>
                  <Input
                    id="volatility"
                    type="number"
                    step="0.1"
                    value={volatility}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setVolatility(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
                <div>
                  <Label className="text-zinc-400 text-xs" htmlFor="currentVolatility">
                    Current IV (%)
                  </Label>
                  <Input
                    id="currentVolatility"
                    type="number"
                    step="0.1"
                    value={currentVolatility}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentVolatility(Number(e.target.value))}
                    className="bg-zinc-950 border-zinc-800 text-zinc-200 text-xs focus:ring-emerald-500/40 mt-1"
                  />
                </div>
              </div>

              {/* DECOMPOSE BUTTON */}
              <div className="pt-2">
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-zinc-50 font-bold transition-all text-xs py-2.5 rounded-lg shadow-lg active:scale-[0.98]"
                >
                  {loading ? "Calculating Greeks & Taylor Decay..." : "Run Taylor Decomposer"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* DYNAMIC RESULTS COLUMN */}
          <div className="lg:col-span-1 space-y-6">
            {error && (
              <Card className="bg-rose-950/20 border-rose-900 text-rose-300">
                <CardContent className="pt-6 flex items-start gap-2.5">
                  <AlertCircle className="h-5 w-5 text-rose-500 shrink-0" />
                  <div className="text-xs">
                    <p className="font-bold">Execution Error</p>
                    <p className="mt-1 leading-relaxed">{error}</p>
                  </div>
                </CardContent>
              </Card>
            )}

            {!result && !error && (
              <Card className="bg-zinc-900/10 border-zinc-850 h-full flex flex-col justify-center items-center py-16 text-center">
                <CardContent className="space-y-3">
                  <HelpCircle className="h-8 w-8 text-zinc-600" />
                  <p className="text-sm font-semibold text-zinc-400">Ready to Decompose</p>
                  <p className="text-xs text-zinc-500 max-w-[200px] leading-relaxed">
                    Set option variables and trigger calculations to decompose gains/losses.
                  </p>
                </CardContent>
              </Card>
            )}

            {result && (
              <Card className="bg-zinc-900/40 border-zinc-800/80 shadow-2xl">
                <CardHeader>
                  <CardTitle className="text-zinc-200 text-sm font-semibold uppercase tracking-wider">
                    Position P&L Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Summary string */}
                  <div className="bg-emerald-950/20 border border-emerald-900/50 p-4 rounded-lg flex gap-2.5 items-start">
                    <TrendingUp className="h-4.5 w-4.5 text-emerald-400 shrink-0 mt-0.5" />
                    <p className="text-xs leading-relaxed text-zinc-300">
                      {result.summary}
                    </p>
                  </div>

                  {/* Net P&L metrics */}
                  <div className="flex justify-between border-b border-zinc-800 pb-2">
                    <span className="text-xs text-zinc-400">Calculated Net P&L</span>
                    <span
                      className={`text-xs font-bold ${
                        result.total_pnl >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      ₹{result.total_pnl.toFixed(2)}
                    </span>
                  </div>
                  
                  {/* Residual value check */}
                  <div className="flex justify-between text-[11px] text-zinc-500">
                    <span>Taylor Series Residual Error</span>
                    <span>₹{result.residual.toFixed(2)}</span>
                  </div>
                  {Math.abs(result.residual) > 0.15 * Math.abs(result.total_pnl) && (
                    <div className="bg-amber-950/20 border border-amber-900/50 p-2.5 rounded-lg flex gap-2 items-start text-[11px] text-amber-300/90 mt-1">
                      <AlertCircle className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
                      <span>
                        Large residual — first-order approximation is less accurate for big moves; treat this breakdown as directional, not exact.
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </form>

        {/* RECHARTS WATERFALL / COMPARATIVE GRAPH */}
        {result && (
          <Card className="bg-zinc-900/40 border-zinc-800/70 p-6 shadow-2xl">
            <CardHeader className="px-0 pt-0 pb-4">
              <CardTitle className="text-sm font-semibold uppercase text-zinc-400 tracking-wider">
                Greeks Contribution Waterfall (First-Order Taylor Series)
              </CardTitle>
            </CardHeader>
            <CardContent className="h-80 px-0 pb-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="name" stroke="#71717a" />
                  <YAxis stroke="#71717a" label={{ value: 'P&L Contribution (₹)', angle: -90, position: 'insideLeft', fill: '#71717a' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46" }}
                    labelStyle={{ color: "#f4f4f5", fontWeight: "bold" }}
                  />
                  <Bar dataKey="value" strokeWidth={1}>
                    {chartData.map((entry, idx) => (
                      <Cell
                        key={`cell-${idx}`}
                        fill={entry.value >= 0 ? "#10b981" : "#f43f5e"}
                        fillOpacity={0.4}
                        stroke={entry.value >= 0 ? "#10b981" : "#f43f5e"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};
export default PnlPage;
