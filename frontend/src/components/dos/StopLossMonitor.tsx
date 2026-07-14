import React from 'react';
import { ChevronUp, ChevronDown, ShieldAlert } from 'lucide-react';

interface GradientGaugeProps {
  percentage: number;
}

export const GradientGauge: React.FC<GradientGaugeProps> = ({ percentage }) => {
  return (
    <div className="space-y-1.5 w-full">
      <div className="flex justify-between items-center text-xs text-zinc-400 font-mono">
        <span className="font-semibold text-zinc-300">% to SL</span>
        <span className="font-bold text-zinc-200">{percentage.toFixed(0)}%</span>
      </div>
      <div className="relative h-3 w-full bg-zinc-950 rounded-full overflow-hidden border border-zinc-800">
        <div
          className="absolute inset-0 rounded-full overflow-hidden transition-all duration-300"
          style={{ width: `${percentage}%` }}
        >
          <div className="h-full w-[calc(100%/var(--pct,1))] bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500" style={{ width: `${(100 / Math.max(percentage, 1)) * 100}%` }} />
        </div>
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"
          style={{ left: "100%" }}
        />
      </div>
    </div>
  );
};

export interface StopLossMonitorProps {
  entryPremium: number;
  currentPremium: number;
  initialSlLevel: number;
  trailingSlLevel: number | null;
  dayType: 'wednesday' | 'thursday';
  isBreached: boolean;
  breachReason: 'initial' | 'trailing' | null;
  lotSize: number;
}

export const StopLossMonitor: React.FC<StopLossMonitorProps> = ({
  entryPremium,
  currentPremium,
  initialSlLevel,
  trailingSlLevel,
  dayType,
  isBreached,
  breachReason,
  lotSize,
}) => {
  const delta = currentPremium - entryPremium;
  const isUp = delta > 0;
  
  // Compute percentage from entryPremium to initialSlLevel
  const pctToSl = Math.min(
    100,
    Math.max(
      0,
      ((currentPremium - entryPremium) / (initialSlLevel - entryPremium)) * 100
    )
  );

  const unrealizedPnL = (entryPremium - currentPremium) * lotSize;

  return (
    <div className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-5 backdrop-blur-md shadow-lg space-y-4">
      {/* Header with Day Type badge and status */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">
              DOS Active Trade Monitor
            </h3>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border capitalize ${
              dayType === 'wednesday' 
                ? 'bg-indigo-950/60 text-indigo-400 border-indigo-900/60' 
                : 'bg-purple-950/60 text-purple-400 border-purple-900/60'
            }`}>
              {dayType}
            </span>
          </div>
          <p className="text-[11px] text-zinc-400 font-mono">
            Auto-executing paper-trading engine (Lot Size: {lotSize})
          </p>
        </div>
        <div>
          {isBreached ? (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950 text-red-400 border border-red-900 animate-pulse flex items-center gap-1">
              <ShieldAlert className="h-3 w-3" /> BREACHED
            </span>
          ) : (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-900">
              ACTIVE SHORT
            </span>
          )}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-zinc-950/40 p-4 rounded-lg border border-zinc-900/60">
        <div>
          <span className="block text-[10px] text-zinc-500 uppercase font-semibold font-mono">Entry Price</span>
          <span className="text-sm font-mono font-semibold text-zinc-200">
            ₹{entryPremium.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="block text-[10px] text-zinc-500 uppercase font-semibold font-mono">Current Premium</span>
          <div className="flex items-center gap-1">
            <span className={`text-sm font-mono font-semibold ${isUp ? 'text-red-400' : 'text-emerald-400'}`}>
              ₹{currentPremium.toFixed(2)}
            </span>
            {/* Premium Delta Chevron */}
            {isUp ? (
              <ChevronUp className="h-4 w-4 text-red-400 shrink-0" />
            ) : (
              <ChevronDown className="h-4 w-4 text-emerald-400 shrink-0" />
            )}
          </div>
        </div>
        <div>
          <span className="block text-[10px] text-zinc-500 uppercase font-semibold font-mono">Initial SL</span>
          <span className="text-sm font-mono font-semibold text-red-400">
            ₹{initialSlLevel.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="block text-[10px] text-zinc-500 uppercase font-semibold font-mono">Unrealized P&L</span>
          <span className={`text-sm font-mono font-bold ${unrealizedPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {unrealizedPnL >= 0 ? '+' : ''}₹{unrealizedPnL.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Gradient Gauge component */}
      <GradientGauge percentage={pctToSl} />

      {/* Breached alert view with Fix 2: null-safe trailingSlLevel fallback */}
      {isBreached && (
        <div className="bg-red-950/20 border border-red-900/50 rounded-lg p-3 text-xs text-red-400 space-y-1">
          <p className="font-semibold">
            🚨 Trade Stopped Out
          </p>
          <p>
            Triggered at price: <span className="font-mono font-semibold">{(breachReason === 'initial' ? initialSlLevel : (trailingSlLevel ?? 0)).toFixed(2)}</span> ({breachReason} SL)
          </p>
        </div>
      )}

      {/* Trailing SL placeholder check */}
      {trailingSlLevel !== null && (
        <div className="text-[10px] text-zinc-500 italic">
          Trailing SL Gauge active at {(trailingSlLevel ?? 0).toFixed(2)}
        </div>
      )}
    </div>
  );
};
