import React, { useState, useEffect, useMemo } from "react";
import { mockOptionChainResponse } from "../mockData";
import type { OptionChainResponse } from "../mockData";
import { FreshnessBadge } from "../components/FreshnessBadge";
import { fetchOptionChain } from "../api/optionChain";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowUpRight, Layers, Flame, TrendingUp } from "lucide-react";

export const OptionChainPage: React.FC = () => {
  const [data, setData] = useState<OptionChainResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (isInitial: boolean) => {
    try {
      if (isInitial) setLoading(true);
      const res = await fetchOptionChain("NIFTY");
      setData(res);
      setError(null);
    } catch (err: any) {
      const errMsg = err.message || "Failed to connect to backend api";
      console.error("Error fetching option chain:", errMsg);
      setError(errMsg);
      // Fallback to mockData on initial error so page is not empty
      setData((prev) => prev || mockOptionChainResponse);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(true);
    const interval = setInterval(() => fetchData(false), 8000);
    return () => {
      clearInterval(interval);
    };
  }, []);

  // Use data state or fallback to mockData if null
  const response = data || mockOptionChainResponse;
  const chainData = response.data;
  const spot = chainData.records.underlyingValue;
  const timestamp = chainData.records.timestamp;
  const strikes = chainData.records.data;

  // Helper formatting functions
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-IN").format(num);
  };

  const formatRupee = (num: number) => {
    return "₹" + new Intl.NumberFormat("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  // Compute PCR (Put-Call Ratio) dynamically
  const pcrMetrics = useMemo(() => {
    let totalCallOI = 0;
    let totalPutOI = 0;
    strikes.forEach((item) => {
      if (item.CE) totalCallOI += item.CE.openInterest;
      if (item.PE) totalPutOI += item.PE.openInterest;
    });

    const ratio = totalCallOI > 0 ? totalPutOI / totalCallOI : 0;
    
    let sentiment = "Neutral";
    if (ratio > 1.2) sentiment = "Bullish (Overbought Puts / Put writing)";
    else if (ratio > 1.05) sentiment = "Mildly Bullish";
    else if (ratio < 0.8) sentiment = "Bearish (Call writing)";
    else if (ratio < 0.95) sentiment = "Mildly Bearish";

    return {
      totalCallOI,
      totalPutOI,
      ratio: Number(ratio.toFixed(3)),
      sentiment,
    };
  }, [strikes]);

  // Compute Max Pain dynamically
  const maxPainStrike = useMemo(() => {
    const candidateStrikes = strikes.map((s) => s.strikePrice);
    let minPainStrike = candidateStrikes[0];
    let minPainValue = Infinity;

    candidateStrikes.forEach((targetK) => {
      let totalPain = 0;
      strikes.forEach((item) => {
        if (item.CE) {
          const payout = Math.max(targetK - item.strikePrice, 0);
          totalPain += item.CE.openInterest * payout;
        }
        if (item.PE) {
          const payout = Math.max(item.strikePrice - targetK, 0);
          totalPain += item.PE.openInterest * payout;
        }
      });

      if (totalPain < minPainValue) {
        minPainValue = totalPain;
        minPainStrike = targetK;
      }
    });

    return minPainStrike;
  }, [strikes]);

  // Max OI calculations for inline bar heatmaps
  const { maxCeOI, maxPeOI } = useMemo(() => {
    let ceMax = 0;
    let peMax = 0;
    strikes.forEach((item) => {
      if (item.CE && item.CE.openInterest > ceMax) ceMax = item.CE.openInterest;
      if (item.PE && item.PE.openInterest > peMax) peMax = item.PE.openInterest;
    });
    return { maxCeOI: ceMax, maxPeOI: peMax };
  }, [strikes]);

  if (loading && !data) {
    return (
      <div className="flex-1 flex flex-col bg-zinc-950 text-zinc-100 overflow-y-auto">
        {/* STICKY HEADER SKELETON */}
        <header className="sticky top-0 z-20 bg-zinc-950 border-b border-zinc-800/80 px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6 animate-pulse">
            <div>
              <div className="h-3 bg-zinc-850 rounded w-16" />
              <div className="h-6 bg-zinc-800 rounded w-24 mt-1" />
            </div>
            <div className="h-8 w-px bg-zinc-800" />
            <div>
              <div className="h-3 bg-zinc-850 rounded w-16" />
              <div className="h-6 bg-zinc-800 rounded w-32 mt-1" />
            </div>
          </div>
          <div className="h-8 bg-zinc-850 rounded w-40 animate-pulse" />
        </header>

        {/* Skeleton Loader Main Content */}
        <div className="p-8 space-y-8 flex-1 max-w-7xl w-full mx-auto animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="bg-zinc-900/40 border-zinc-800/70 h-28">
                <CardHeader className="pb-2">
                  <div className="h-3 bg-zinc-850 rounded w-1/3" />
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-zinc-800 rounded w-1/2 mt-1" />
                  <div className="h-3 bg-zinc-900 rounded w-2/3 mt-2" />
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="border border-zinc-800 bg-zinc-900/20 rounded-xl overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/40 flex justify-between">
              <div className="h-4 bg-zinc-850 rounded w-1/4" />
              <div className="h-3 bg-zinc-850 rounded w-1/6" />
            </div>
            <div className="p-6 space-y-4">
              <div className="h-8 bg-zinc-900 rounded w-full" />
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => (
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
      {error && (
        <div className="bg-amber-950/40 border-b border-amber-900/60 px-8 py-2 text-xs flex items-center justify-between text-amber-300">
          <span>Using cached local data. Connection failed: {error}</span>
          <span className="font-semibold text-[10px] text-amber-500 font-mono tracking-wider animate-pulse uppercase">
            Retrying...
          </span>
        </div>
      )}
      
      {/* STICKY HEADER */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-zinc-950/85 border-b border-zinc-800/80 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div>
            <span className="text-zinc-500 font-semibold text-xs uppercase tracking-wider">
              Underlying Asset
            </span>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="font-bold text-xl text-zinc-100">NIFTY 50</span>
              <span className="text-zinc-500 text-[10px] font-mono">Index (NSE: {timestamp})</span>
            </div>
          </div>
          <div className="h-8 w-px bg-zinc-800" />
          <div>
            <span className="text-zinc-500 font-semibold text-xs uppercase tracking-wider">
              Spot Price
            </span>
            <div className="flex items-baseline gap-3 mt-0.5">
              <span className="font-mono font-bold text-xl text-emerald-400">
                {formatRupee(spot)}
              </span>
              <span className="text-emerald-500 text-xs font-semibold flex items-center gap-0.5">
                <ArrowUpRight className="h-3 w-3" />
                +112.40 (+0.47%)
              </span>
            </div>
          </div>
        </div>
        
        {/* Freshness Badge Component */}
        <FreshnessBadge
          fetchedAt={response.fetched_at}
          ageMinutes={response.age_minutes}
          source={response.source}
        />
      </header>

      {/* PAGE CONTAINER */}
      <main className="p-8 space-y-8 flex-1 max-w-7xl w-full mx-auto">
        
        {/* SUMMARY CARDS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* PCR Card */}
          <Card className="bg-zinc-900/40 border-zinc-800/70">
            <CardHeader className="pb-2">
              <CardTitle className="text-zinc-400 text-xs font-semibold uppercase tracking-wider flex items-center justify-between">
                <span>Put-Call Ratio (PCR)</span>
                <TrendingUp className="h-4 w-4 text-emerald-500" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-zinc-100">
                {pcrMetrics.ratio}
              </div>
              <p className="text-[11px] text-zinc-500 mt-1 leading-normal">
                Sentiment: <span className="text-zinc-300 font-medium">{pcrMetrics.sentiment}</span>
              </p>
            </CardContent>
          </Card>

          {/* Max Pain Card */}
          <Card className="bg-zinc-900/40 border-zinc-800/70">
            <CardHeader className="pb-2">
              <CardTitle className="text-zinc-400 text-xs font-semibold uppercase tracking-wider flex items-center justify-between">
                <span>Max Pain Strike</span>
                <Flame className="h-4 w-4 text-orange-500" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-zinc-100">
                {formatNumber(maxPainStrike)}
              </div>
              <p className="text-[11px] text-zinc-500 mt-1 leading-normal">
                Strike with minimum buyer payout on expiry.
              </p>
            </CardContent>
          </Card>

          {/* Expiry / Spot Summary Card */}
          <Card className="bg-zinc-900/40 border-zinc-800/70">
            <CardHeader className="pb-2">
              <CardTitle className="text-zinc-400 text-xs font-semibold uppercase tracking-wider flex items-center justify-between">
                <span>Current Expiry</span>
                <Layers className="h-4 w-4 text-blue-500" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-bold text-zinc-100">
                {strikes[0]?.expiryDate || "N/A"}
              </div>
              <p className="text-[11px] text-zinc-500 mt-2 leading-normal">
                Weekly option chain cycle.
              </p>
            </CardContent>
          </Card>

        </div>

        {/* OPTION CHAIN TABLE SECTION */}
        <div className="border border-zinc-800 bg-zinc-900/20 rounded-xl overflow-hidden shadow-2xl">
          
          <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/40 flex items-center justify-between">
            <h3 className="font-semibold text-sm text-zinc-200">
              Derivatives Option Chain
            </h3>
            <div className="flex gap-4 text-xs font-semibold text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500/20 border border-emerald-500" />
                CE (Calls)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-red-500/20 border border-red-500" />
                PE (Puts)
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-zinc-950/80 border-b border-zinc-800 font-mono text-[10px] text-zinc-400">
                <TableRow className="hover:bg-transparent border-zinc-800">
                  <TableHead className="text-center font-semibold border-r border-zinc-800" colSpan={5}>
                    CALLS (CE)
                  </TableHead>
                  <TableHead className="text-center bg-zinc-950 font-bold border-r border-zinc-800" rowSpan={2}>
                    STRIKE
                  </TableHead>
                  <TableHead className="text-center font-semibold" colSpan={5}>
                    PUTS (PE)
                  </TableHead>
                </TableRow>
                <TableRow className="hover:bg-transparent border-zinc-800">
                  {/* CE headers */}
                  <TableHead className="text-right">OI (Lakhs)</TableHead>
                  <TableHead className="text-right">Chg OI</TableHead>
                  <TableHead className="text-right">Volume</TableHead>
                  <TableHead className="text-right">IV (%)</TableHead>
                  <TableHead className="text-right border-r border-zinc-800 text-zinc-200 font-bold">LTP</TableHead>
                  
                  {/* PE headers */}
                  <TableHead className="text-left text-zinc-200 font-bold">LTP</TableHead>
                  <TableHead className="text-left">IV (%)</TableHead>
                  <TableHead className="text-left">Volume</TableHead>
                  <TableHead className="text-left">Chg OI</TableHead>
                  <TableHead className="text-left">OI (Lakhs)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="font-mono text-xs">
                {strikes.map((row) => {
                  const strikePrice = row.strikePrice;
                  
                  // ITM logic: Call ITM if strike < spot; Put ITM if strike > spot
                  const isCallITM = strikePrice < spot;
                  const isPutITM = strikePrice > spot;
                  
                  // CE metrics
                  const ceOI = row.CE?.openInterest || 0;
                  const ceChg = row.CE?.changeinOpenInterest || 0;
                  const ceVol = row.CE?.totalTradedVolume || 0;
                  const ceIV = row.CE?.impliedVolatility || 0;
                  const ceLtp = row.CE?.lastPrice || 0;

                  // PE metrics
                  const peOI = row.PE?.openInterest || 0;
                  const peChg = row.PE?.changeinOpenInterest || 0;
                  const peVol = row.PE?.totalTradedVolume || 0;
                  const peIV = row.PE?.impliedVolatility || 0;
                  const peLtp = row.PE?.lastPrice || 0;

                  // Percent calculation for heatmap bar
                  const cePercent = maxCeOI > 0 ? (ceOI / maxCeOI) * 100 : 0;
                  const pePercent = maxPeOI > 0 ? (peOI / maxPeOI) * 100 : 0;

                  return (
                    <TableRow
                      key={strikePrice}
                      className="hover:bg-zinc-850/50 border-zinc-850/60 transition-colors"
                    >
                      {/* CE Cells */}
                      {/* CE OI with custom right-to-left background progress bar */}
                      <TableCell className={`text-right relative ${isCallITM ? "bg-emerald-950/10" : ""}`}>
                        <div
                          className="absolute right-0 top-0 bottom-0 bg-emerald-500/5 pointer-events-none"
                          style={{ width: `${cePercent}%` }}
                        />
                        <span className="relative z-10 font-medium">
                          {formatNumber(ceOI)}
                        </span>
                      </TableCell>
                      
                      <TableCell className={`text-right ${isCallITM ? "bg-emerald-950/10" : ""}`}>
                        <span
                          className={`inline-flex items-center gap-0.5 ${
                            ceChg >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {ceChg >= 0 ? "+" : ""}
                          {formatNumber(ceChg)}
                        </span>
                      </TableCell>
                      
                      <TableCell className={`text-right ${isCallITM ? "bg-emerald-950/10" : ""}`}>
                        {formatNumber(ceVol)}
                      </TableCell>
                      
                      <TableCell className={`text-right ${isCallITM ? "bg-emerald-950/10" : ""}`}>
                        {ceIV.toFixed(2)}
                      </TableCell>
                      
                      <TableCell className={`text-right border-r border-zinc-850 font-bold text-zinc-100 ${isCallITM ? "bg-emerald-900/15" : ""}`}>
                        {formatRupee(ceLtp)}
                      </TableCell>

                      {/* STRIKE PRICE (Center Column) */}
                      <TableCell className="text-center font-bold font-mono bg-zinc-950 text-zinc-200 border-r border-zinc-850 py-3 shadow-inner">
                        {formatNumber(strikePrice)}
                      </TableCell>

                      {/* PE Cells */}
                      <TableCell className={`text-left font-bold text-zinc-100 ${isPutITM ? "bg-rose-900/15" : ""}`}>
                        {formatRupee(peLtp)}
                      </TableCell>
                      
                      <TableCell className={`text-left ${isPutITM ? "bg-rose-950/10" : ""}`}>
                        {peIV.toFixed(2)}
                      </TableCell>
                      
                      <TableCell className={`text-left ${isPutITM ? "bg-rose-950/10" : ""}`}>
                        {formatNumber(peVol)}
                      </TableCell>
                      
                      <TableCell className={`text-left ${isPutITM ? "bg-rose-950/10" : ""}`}>
                        <span
                          className={`inline-flex items-center gap-0.5 ${
                            peChg >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {peChg >= 0 ? "+" : ""}
                          {formatNumber(peChg)}
                        </span>
                      </TableCell>

                      {/* PE OI with custom left-to-right background progress bar */}
                      <TableCell className={`text-left relative ${isPutITM ? "bg-rose-950/10" : ""}`}>
                        <div
                          className="absolute left-0 top-0 bottom-0 bg-rose-500/5 pointer-events-none"
                          style={{ width: `${pePercent}%` }}
                        />
                        <span className="relative z-10 font-medium">
                          {formatNumber(peOI)}
                        </span>
                      </TableCell>

                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          
        </div>

      </main>
    </div>
  );
};
export default OptionChainPage;
