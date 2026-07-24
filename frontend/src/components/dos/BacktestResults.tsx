import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { BacktestSummary, EquityPoint } from "../../api/dos";

// ---------------------------------------------------------------------------
// Equity Curve
// ---------------------------------------------------------------------------

const EquityCurveChart: React.FC<{ equityCurve: EquityPoint[] }> = ({ equityCurve }) => {
  const lastPoint = equityCurve[equityCurve.length - 1];
  const endedPositive = lastPoint ? lastPoint.cumulative_pnl >= 0 : true;
  const lineColor = endedPositive ? "#10b981" : "#ef4444";
  const gradientId = endedPositive ? "colorGreen" : "colorRed";

  const fmt = (v: number) =>
    `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={equityCurve} margin={{ top: 8, right: 16, left: 8, bottom: 4 }}>
        <defs>
          <linearGradient id="colorGreen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="colorRed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
        <XAxis
          dataKey="trade_date"
          tick={{ fill: "#71717a", fontSize: 11, fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={fmt}
          tick={{ fill: "#71717a", fontSize: 11, fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
          width={80}
        />
        <Tooltip
          contentStyle={{
            background: "#18181b",
            border: "1px solid #3f3f46",
            borderRadius: 10,
            fontSize: 12,
            fontFamily: "monospace",
          }}
          labelStyle={{ color: "#a1a1aa" }}
          formatter={(value) => [fmt(typeof value === "number" ? value : Number(value ?? 0)), "Cumulative P&L"]}
        />
        <ReferenceLine y={0} stroke="#52525b" strokeDasharray="4 4" />
        <Area
          type="monotone"
          dataKey="cumulative_pnl"
          stroke={lineColor}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          dot={{ r: 4, fill: lineColor, strokeWidth: 0 }}
          activeDot={{ r: 6, fill: lineColor }}
          isAnimationActive={true}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

const StatCard: React.FC<{
  label: string;
  value: string;
  sub?: string;
  accent?: "green" | "red" | "indigo" | "default";
}> = ({ label, value, sub, accent = "default" }) => {
  const accentClass = {
    green: "text-emerald-400",
    red: "text-red-400",
    indigo: "text-indigo-400",
    default: "text-zinc-100",
  }[accent];

  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-4 flex flex-col gap-1">
      <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">{label}</span>
      <span className={`text-2xl font-bold font-mono ${accentClass}`}>{value}</span>
      {sub && <span className="text-[11px] text-zinc-600 font-mono">{sub}</span>}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Trade table row
// ---------------------------------------------------------------------------

const TradeRow: React.FC<{ trade: BacktestSummary["trades"][number]; index: number }> = ({
  trade,
  index,
}) => {
  const pnlPositive = trade.pnl >= 0;
  const fmt = (v: number) =>
    `₹${Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <tr
      className={`border-b border-zinc-800/50 transition-colors hover:bg-zinc-800/20 ${
        index % 2 === 0 ? "bg-zinc-900/10" : ""
      }`}
    >
      <td className="py-3 px-4 text-xs font-mono text-zinc-400">{trade.trade_date}</td>
      <td className="py-3 px-4">
        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 bg-zinc-800/60 px-2 py-0.5 rounded-full">
          {trade.day_type}
        </span>
      </td>
      <td className="py-3 px-4">
        <span
          className={`text-xs font-bold font-mono ${
            trade.option_side === "CE" ? "text-emerald-400" : "text-rose-400"
          }`}
        >
          {trade.strike} {trade.option_side}
        </span>
      </td>
      <td className="py-3 px-4 text-xs font-mono text-zinc-300">{fmt(trade.entry_price)}</td>
      <td className="py-3 px-4 text-xs font-mono text-zinc-300">{fmt(trade.exit_price)}</td>
      <td className="py-3 px-4">
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
            trade.exit_reason === "initial_sl"
              ? "bg-red-500/15 text-red-400 border border-red-500/30"
              : "bg-zinc-800/60 text-zinc-400 border border-zinc-700/40"
          }`}
        >
          {trade.exit_reason === "initial_sl" ? "SL Hit" : "Market Close"}
        </span>
      </td>
      <td className="py-3 px-4 text-right">
        <span className={`text-sm font-bold font-mono ${pnlPositive ? "text-emerald-400" : "text-red-400"}`}>
          {pnlPositive ? "+" : "−"}{fmt(trade.pnl)}
        </span>
      </td>
    </tr>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const getWeeksCount = (summary: BacktestSummary): number => {
  const dateStrs = [
    ...(summary.equity_curve ?? []).map((p) => p.trade_date),
    ...(summary.trades ?? []).map((t) => t.trade_date),
    ...(summary.errors ?? []).map((e) => e.trade_date),
  ].filter(Boolean);

  if (dateStrs.length === 0) {
    return summary.total_trades_attempted ? Math.ceil(summary.total_trades_attempted / 2) : 8;
  }

  const timestamps = dateStrs
    .map((d) => new Date(d).getTime())
    .filter((t) => !isNaN(t));

  if (timestamps.length === 0) {
    return summary.total_trades_attempted ? Math.ceil(summary.total_trades_attempted / 2) : 8;
  }

  const minTime = Math.min(...timestamps);
  const maxTime = Math.max(...timestamps);
  const diffDays = (maxTime - minTime) / (1000 * 60 * 60 * 24);

  return Math.max(1, Math.ceil((diffDays + 1) / 7));
};

export const BacktestResults: React.FC<{ summary: BacktestSummary }> = ({ summary }) => {
  const totalPnlPositive = summary.total_pnl >= 0;
  const weeksCount = getWeeksCount(summary);

  const fmtRupees = (v: number | null) =>
    v === null
      ? "--"
      : `${v >= 0 ? "+" : "−"}₹${Math.abs(v).toLocaleString("en-IN", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`;

  return (
    <div className="space-y-6">
      {/* Summary stat strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard
          label="Total Trades"
          value={String(summary.total_trades_attempted)}
          sub={`${summary.successful_trades} succeeded`}
          accent="default"
        />
        <StatCard
          label="Win Rate"
          value={summary.win_rate_pct !== null ? `${summary.win_rate_pct}%` : "--"}
          sub="profitable days"
          accent={
            summary.win_rate_pct !== null && summary.win_rate_pct >= 50 ? "green" : "red"
          }
        />
        <StatCard
          label="Total P&L"
          value={fmtRupees(summary.total_pnl)}
          sub={`${weeksCount} week${weeksCount === 1 ? "" : "s"}, 1 lot`}
          accent={totalPnlPositive ? "green" : "red"}
        />
        <StatCard
          label="Avg P&L / Trade"
          value={fmtRupees(summary.avg_pnl)}
          accent={
            summary.avg_pnl !== null && summary.avg_pnl >= 0 ? "green" : "red"
          }
        />
        <StatCard
          label="SL Hit Rate"
          value={
            summary.initial_sl_hit_rate_pct !== null
              ? `${summary.initial_sl_hit_rate_pct}%`
              : "--"
          }
          sub="of successful trades"
          accent="indigo"
        />
        <StatCard
          label="Failed Days"
          value={String(summary.failed_trades)}
          sub="data / fetch errors"
          accent={summary.failed_trades > 0 ? "red" : "default"}
        />
      </div>

      {/* Equity curve */}
      <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500 font-mono">
            Equity Curve
          </span>
          <span
            className={`text-sm font-bold font-mono ${
              totalPnlPositive ? "text-emerald-400" : "text-red-400"
            }`}
          >
            Net {fmtRupees(summary.total_pnl)}
          </span>
        </div>
        {summary.equity_curve.length > 0 ? (
          <EquityCurveChart equityCurve={summary.equity_curve} />
        ) : (
          <div className="h-[220px] flex items-center justify-center text-zinc-600 text-sm font-mono">
            No equity data
          </div>
        )}
      </div>

      {/* Trade table */}
      <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-800">
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500 font-mono">
            Trade Log
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800">
                {["Date", "Day", "Contract", "Entry", "Exit", "Reason", "P&L"].map((h) => (
                  <th
                    key={h}
                    className={`py-2 px-4 text-[10px] font-mono uppercase tracking-widest text-zinc-600 font-semibold ${
                      h === "P&L" ? "text-right" : "text-left"
                    }`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {summary.trades.map((t, i) => (
                <TradeRow key={`${t.trade_date}-${i}`} trade={t} index={i} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Errors section (only if any) */}
      {summary.errors.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 space-y-2">
          <span className="text-[10px] font-mono uppercase tracking-widest text-amber-600">
            Data Gaps ({summary.errors.length})
          </span>
          {summary.errors.map((e) => (
            <div key={e.trade_date} className="text-xs font-mono text-amber-400/80">
              <span className="text-amber-500">{e.trade_date}:</span> {e.error}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
