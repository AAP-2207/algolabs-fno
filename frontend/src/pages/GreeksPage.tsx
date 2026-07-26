import React, { useState, useEffect, useMemo } from "react";
import { fetchGreeks } from "../api/greeks";
import type { GreeksResponse } from "../api/greeks";
import { FreshnessBadge } from "../components/FreshnessBadge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { Activity, AlertTriangle, Info, TrendingUp } from "lucide-react";
import { VolatilitySurface3D } from "../components/VolatilitySurface3D";


// Local Greeks Fallback Data in case the backend is loading or offline
const fallbackGreeksData: GreeksResponse = {
  fetched_at: new Date().toISOString(),
  source: "mock",
  age_minutes: 0.0,
  strikes: [23900, 24000, 24100, 24200, 24250, 24300, 24400, 24500, 24600].map((strike) => {
    const spot = 24248.50;
    const isCallITM = strike < spot;
    const isPutITM = strike > spot;
    const distance = Math.abs(strike - spot);
    const nseIv = 11.5 + (distance / spot) * 120;
    const computedIv = nseIv + (Math.random() > 0.8 ? (Math.random() * 2.5 - 1.2) : 0);

    const cePrice = Math.max(spot - strike, 0) + 120;
    const pePrice = Math.max(strike - spot, 0) + 120;

    return {
      strike,
      CE: {
        delta: isCallITM ? 0.82 : 0.24,
        gamma: 0.0015,
        theta: -12.45,
        vega: 18.2,
        computed_iv: computedIv,
        nse_iv: nseIv,
        ltp: cePrice,
      },
      PE: {
        delta: isPutITM ? -0.81 : -0.22,
        gamma: 0.0014,
        theta: -10.82,
        vega: 17.5,
        computed_iv: computedIv + 0.1,
        nse_iv: nseIv,
        ltp: pePrice,
      },
    };
  }),
};

export const GreeksPage: React.FC = () => {
  const [data, setData] = useState<GreeksResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (isInitial: boolean) => {
    try {
      if (isInitial) setLoading(true);
      const res = await fetchGreeks("NIFTY");
      setData(res);
      setError(null);
    } catch (err: any) {
      const errMsg = err.message || "Failed to fetch greeks data";
      console.error("Greeks fetch error:", errMsg);
      setError(errMsg);
      setData((prev) => prev || fallbackGreeksData);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(true);
    const interval = setInterval(() => fetchData(false), 8000);
    return () => clearInterval(interval);
  }, []);

  const response = data || fallbackGreeksData;
  const strikes = response.strikes;

  // Find approximate spot from data (using first record ltp/strike calculation or constant spot)
  const spot = 24248.50; // default proxy matching our option chain spot

  // Find ATM strike and compare ATM IV to average IV
  const ivMetrics = useMemo(() => {
    let closestStrike = strikes[0]?.strike || 24250;
    let minDiff = Infinity;
    let sumIV = 0;
    let countIV = 0;

    strikes.forEach((item) => {
      const diff = Math.abs(item.strike - spot);
      if (diff < minDiff) {
        minDiff = diff;
        closestStrike = item.strike;
      }
      if (item.CE && item.CE.computed_iv > 0) {
        sumIV += item.CE.computed_iv;
        countIV++;
      }
      if (item.PE && item.PE.computed_iv > 0) {
        sumIV += item.PE.computed_iv;
        countIV++;
      }
    });

    const atmRecord = strikes.find((s) => s.strike === closestStrike);
    const ceAtmIV = atmRecord?.CE?.computed_iv || 0.0;
    const peAtmIV = atmRecord?.PE?.computed_iv || 0.0;
    const atmIV = (ceAtmIV + peAtmIV) / 2 || 12.0;

    const avgIV = countIV > 0 ? sumIV / countIV : 12.0;
    const isSpike = atmIV > avgIV * 1.15; // 15% elevated compared to average smile base

    return {
      atmStrike: closestStrike,
      atmIV: Number(atmIV.toFixed(2)),
      avgIV: Number(avgIV.toFixed(2)),
      isSpike,
    };
  }, [strikes, spot]);

  // Chart Data Mapper for Recharts
  const chartData = useMemo(() => {
    return strikes
      .map((item) => ({
        strike: item.strike,
        CE_IV: item.CE && item.CE.computed_iv > 0 ? Number(item.CE.computed_iv.toFixed(2)) : null,
        PE_IV: item.PE && item.PE.computed_iv > 0 ? Number(item.PE.computed_iv.toFixed(2)) : null,
      }))
      .filter((d) => d.CE_IV !== null || d.PE_IV !== null)
      .sort((a, b) => a.strike - b.strike);
  }, [strikes]);

  // SKELETON LOADER
  if (loading && !data) {
    return (
      <div className="flex-1 flex flex-col bg-zinc-950 text-zinc-100 overflow-y-auto">
        <header className="sticky top-0 z-20 bg-zinc-950 border-b border-zinc-800/85 px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6 animate-pulse">
            <div>
              <div className="h-3 bg-zinc-850 rounded w-16" />
              <div className="h-6 bg-zinc-800 rounded w-40 mt-1" />
            </div>
          </div>
          <div className="h-8 bg-zinc-850 rounded w-40 animate-pulse" />
        </header>

        <div className="p-8 space-y-8 flex-1 max-w-7xl w-full mx-auto animate-pulse">
          <div className="border border-zinc-800 bg-zinc-900/20 rounded-xl overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/40 flex justify-between">
              <div className="h-4 bg-zinc-850 rounded w-1/4" />
              <div className="h-3 bg-zinc-850 rounded w-1/6" />
            </div>
            <div className="p-6 space-y-4">
              <div className="h-8 bg-zinc-900 rounded w-full" />
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-6 bg-zinc-950 rounded w-full" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-zinc-950 text-zinc-100 overflow-y-auto">
      {/* ERROR BANNER */}
      {error && (
        <div className="bg-amber-950/40 border-b border-amber-900 px-8 py-2 text-xs flex items-center justify-between text-amber-300">
          <span>Using cached local greeks data. Fetch error: {error}</span>
          <span className="font-semibold text-[10px] text-amber-500 font-mono tracking-wider animate-pulse uppercase">
            Retrying...
          </span>
        </div>
      )}

      {/* STICKY HEADER */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-zinc-950/85 border-b border-zinc-800/80 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-emerald-500" />
            <h2 className="font-bold text-lg text-zinc-100">Greeks & Implied Volatility Desk</h2>
          </div>
        </div>
        <FreshnessBadge
          fetchedAt={response.fetched_at}
          ageMinutes={response.age_minutes}
          source={response.source}
        />
      </header>

      {/* MAIN CONTAINER */}
      <main className="p-8 space-y-8 flex-1 max-w-7xl w-full mx-auto">
        
        {/* INTERPRETATION CARD */}
        <Card className="bg-zinc-900/40 border-zinc-800/70">
          <CardHeader className="pb-2">
            <CardTitle className="text-zinc-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-2">
              <Info className="h-4 w-4 text-emerald-500" />
              Volatility Smile Interpretation
            </CardTitle>
          </CardHeader>
          <CardContent>
            {ivMetrics.isSpike ? (
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-sm text-zinc-200">IV Spike Detected</h4>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    At-the-money IV ({ivMetrics.atmIV}%) is elevated by more than 15% relative to the average IV ({ivMetrics.avgIV}%) across the smile. This indicates heightening pricing pressure on the index options, potentially reflecting immediate hedging activity, institutional flow, or market anticipation of an impending macroeconomic release.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3">
                <TrendingUp className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-sm text-zinc-200">IV Levels Normal</h4>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    At-the-money IV ({ivMetrics.atmIV}%) is well-aligned with the average IV base of {ivMetrics.avgIV}%. The option pricing shows a standard volatility smile distribution with typical skew features, indicating general stability and absence of outsized indexing risks at this moment.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* GREEKS TABLE */}
        <div className="border border-zinc-800 bg-zinc-900/20 rounded-xl overflow-hidden shadow-2xl">
          <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/40">
            <h3 className="font-semibold text-sm text-zinc-200">Option Contract Greeks</h3>
          </div>
          
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-zinc-950/80 border-b border-zinc-800 font-mono text-[10px] text-zinc-400">
                <TableRow className="hover:bg-transparent border-zinc-800">
                  <TableHead className="text-center font-semibold border-r border-zinc-800" colSpan={5}>
                    CALL GREEKS (CE)
                  </TableHead>
                  <TableHead className="text-center bg-zinc-950 font-bold border-r border-zinc-800" rowSpan={2}>
                    STRIKE
                  </TableHead>
                  <TableHead className="text-center font-semibold" colSpan={5}>
                    PUT GREEKS (PE)
                  </TableHead>
                </TableRow>
                <TableRow className="hover:bg-transparent border-zinc-800">
                  {/* CE Side */}
                  <TableHead className="text-right">Computed IV</TableHead>
                  <TableHead className="text-right">Vega</TableHead>
                  <TableHead className="text-right">Theta</TableHead>
                  <TableHead className="text-right">Gamma</TableHead>
                  <TableHead className="text-right border-r border-zinc-800 text-zinc-300 font-semibold">Delta</TableHead>
                  
                  {/* PE Side */}
                  <TableHead className="text-left text-zinc-300 font-semibold">Delta</TableHead>
                  <TableHead className="text-left">Gamma</TableHead>
                  <TableHead className="text-left">Theta</TableHead>
                  <TableHead className="text-left">Vega</TableHead>
                  <TableHead className="text-left">Computed IV</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="font-mono text-xs">
                {strikes.map((row) => {
                  const strikePrice = row.strike;
                  
                  // CE Detail
                  const ce = row.CE;
                  const ceDelta = ce?.delta ?? 0.0;
                  const ceGamma = ce?.gamma ?? 0.0;
                  const ceTheta = ce?.theta ?? 0.0;
                  const ceVega = ce?.vega ?? 0.0;
                  const ceComputedIV = ce?.computed_iv ?? 0.0;
                  const ceNseIV = ce?.nse_iv ?? 0.0;
                  // Significant divergence check (> 2.0% IV difference)
                  const ceDiverges = ce ? Math.abs(ceComputedIV - ceNseIV) > 2.0 : false;

                  // PE Detail
                  const pe = row.PE;
                  const peDelta = pe?.delta ?? 0.0;
                  const peGamma = pe?.gamma ?? 0.0;
                  const peTheta = pe?.theta ?? 0.0;
                  const peVega = pe?.vega ?? 0.0;
                  const peComputedIV = pe?.computed_iv ?? 0.0;
                  const peNseIV = pe?.nse_iv ?? 0.0;
                  const peDiverges = pe ? Math.abs(peComputedIV - peNseIV) > 2.0 : false;

                  return (
                    <TableRow key={strikePrice} className="hover:bg-zinc-850/50 border-zinc-850/60 transition-colors">
                      {/* CE Cells */}
                      {/* Computed IV */}
                      <TableCell className={`text-right ${ceDiverges ? "text-amber-400 font-semibold bg-amber-950/10" : ""}`}>
                        {ceComputedIV > 0 ? (
                          <span className="flex items-center justify-end gap-1">
                            {ceComputedIV.toFixed(1)}%
                            {ceDiverges && (
                              <span className="cursor-help" title={`Diverges from NSE: ${ceNseIV.toFixed(1)}%`}>
                                <Info className="h-3.5 w-3.5 text-amber-500" />
                              </span>
                            )}
                          </span>
                        ) : "N/A"}
                      </TableCell>
                      <TableCell className="text-right">{ceVega.toFixed(2)}</TableCell>
                      {/* Theta Styled in Red-Orange tones */}
                      <TableCell className="text-right text-orange-400/90 font-medium">
                        {ceTheta.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right">{ceGamma.toFixed(4)}</TableCell>
                      {/* Delta bar gradient (green for calls: 0 to 1) */}
                      <TableCell className="text-right border-r border-zinc-850 min-w-[110px] relative">
                        <div className="absolute right-0 top-0 bottom-0 bg-emerald-500/10" style={{ width: `${Math.max(ceDelta * 100, 0)}%` }} />
                        <span className="relative z-10 font-semibold text-emerald-400">{ceDelta.toFixed(3)}</span>
                      </TableCell>

                      {/* STRIKE PRICE (Center Column) */}
                      <TableCell className="text-center font-bold bg-zinc-950 text-zinc-300 border-r border-zinc-850">
                        {strikePrice}
                      </TableCell>

                      {/* PE Cells */}
                      {/* Delta bar gradient (red for puts: -1 to 0) */}
                      <TableCell className="text-left min-w-[110px] relative">
                        <div className="absolute left-0 top-0 bottom-0 bg-rose-500/10" style={{ width: `${Math.max(Math.abs(peDelta) * 100, 0)}%` }} />
                        <span className="relative z-10 font-semibold text-rose-400">{peDelta.toFixed(3)}</span>
                      </TableCell>
                      <TableCell className="text-left">{peGamma.toFixed(4)}</TableCell>
                      <TableCell className="text-left text-orange-400/90 font-medium">{peTheta.toFixed(2)}</TableCell>
                      <TableCell className="text-left">{peVega.toFixed(2)}</TableCell>
                      {/* Computed IV */}
                      <TableCell className={`text-left ${peDiverges ? "text-amber-400 font-semibold bg-amber-950/10" : ""}`}>
                        {peComputedIV > 0 ? (
                          <span className="flex items-center justify-start gap-1">
                            {peComputedIV.toFixed(1)}%
                            {peDiverges && (
                              <span className="cursor-help" title={`Diverges from NSE: ${peNseIV.toFixed(1)}%`}>
                                <Info className="h-3.5 w-3.5 text-amber-500" />
                              </span>
                            )}
                          </span>
                        ) : "N/A"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* IV SMILE 2D CHART */}
        <Card className="bg-zinc-900/40 border-zinc-800/70 p-6">
          <CardHeader className="px-0 pt-0 pb-4">
            <CardTitle className="text-sm font-semibold uppercase text-zinc-400 tracking-wider">
              Implied Volatility Smile (NIFTY Skew)
            </CardTitle>
          </CardHeader>
          <CardContent className="h-96 px-0 pb-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="strike" stroke="#71717a" tickFormatter={(v) => v.toString()} label={{ value: 'Strike Price', position: 'insideBottom', offset: -5, fill: '#71717a' }} />
                <YAxis stroke="#71717a" label={{ value: 'Implied Volatility (%)', angle: -90, position: 'insideLeft', fill: '#71717a' }} />
                <Tooltip contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46" }} labelStyle={{ color: "#f4f4f5", fontWeight: "bold" }} />
                <Legend verticalAlign="top" height={36} />
                <Line name="Calls (CE IV)" type="monotone" dataKey="CE_IV" stroke="#10b981" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 6 }} connectNulls />
                <Line name="Puts (PE IV)" type="monotone" dataKey="PE_IV" stroke="#f43f5e" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 6 }} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 3D VOLATILITY SURFACE (Strikes x Expiry Dates x IV) */}
        <VolatilitySurface3D symbol="NIFTY" />

      </main>
    </div>
  );
};
export default GreeksPage;

