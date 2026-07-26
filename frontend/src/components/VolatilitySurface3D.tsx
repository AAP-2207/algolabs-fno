import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { AlertTriangle, Info, RefreshCw } from 'lucide-react';

interface SurfacePoint {
  strike: number;
  expiry_date: string;
  days_to_expiry: number;
  option_side: string;
  ltp: number;
  oi: number;
  computed_iv: number;
  nse_iv: number;
}

interface VolSurfaceResponse {
  symbol: string;
  underlying_value: number;
  fetched_at: string;
  source: string;
  note: string;
  raw_points_count: number;
  filtered_points_count: number;
  distinct_expiries_count: number;
  distinct_strikes_count: number;
  expiries: string[];
  points: SurfacePoint[];
}

interface VolatilitySurface3DProps {
  symbol?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const VolatilitySurface3D: React.FC<VolatilitySurface3DProps> = ({ symbol = 'NIFTY' }) => {
  const [data, setData] = useState<VolSurfaceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSurfaceData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/vol-surface?symbol=${encodeURIComponent(symbol)}`);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const json: VolSurfaceResponse = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || 'Failed to load 3D Volatility Surface data');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchSurfaceData();
  }, [symbol]);

  if (loading) {
    return (
      <div className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-6 w-56 bg-zinc-800 rounded"></div>
          <div className="h-5 w-40 bg-zinc-800 rounded"></div>
        </div>
        <div className="h-96 w-full bg-zinc-800/50 rounded-lg flex items-center justify-center">
          <div className="flex items-center space-x-2 text-zinc-400">
            <RefreshCw className="h-5 w-5 animate-spin" />
            <span>Loading 3D Volatility Surface...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data || data.distinct_expiries_count < 2 || data.points.length === 0) {
    return (
      <div className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm">
        <h3 className="text-lg font-semibold text-zinc-100 mb-2">Volatility Surface (3D)</h3>
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-300 flex items-start space-x-3">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Insufficient Data for 3D Volatility Surface</p>
            <p className="text-sm text-amber-400/90 mt-1">
              {error || 'Not enough liquid multi-expiry data available to render a 3D surface right now.'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Organize points into 3D grid matrices (Strikes x Expiries x IV)
  const expiries = data.expiries;
  const strikes = Array.from(new Set(data.points.map((p) => p.strike))).sort((a, b) => a - b);

  // Map for fast lookup (expiry_date -> strike -> avg IV)
  const ivMap: Record<string, Record<number, number>> = {};
  data.points.forEach((pt) => {
    if (!ivMap[pt.expiry_date]) ivMap[pt.expiry_date] = {};
    // Average CE and PE IV for clean surface visualization
    if (ivMap[pt.expiry_date][pt.strike] !== undefined) {
      ivMap[pt.expiry_date][pt.strike] = (ivMap[pt.expiry_date][pt.strike] + pt.computed_iv) / 2;
    } else {
      ivMap[pt.expiry_date][pt.strike] = pt.computed_iv;
    }
  });

  // Calculate Days to Expiry for Y axis labels
  const daysToExpiryMap: Record<string, number> = {};
  data.points.forEach((pt) => {
    daysToExpiryMap[pt.expiry_date] = pt.days_to_expiry;
  });

  const yLabels = expiries.map((exp) => `${daysToExpiryMap[exp] || 0}d (${exp})`);
  const zMatrix: number[][] = expiries.map((exp) => {
    return strikes.map((stk) => {
      const val = ivMap[exp]?.[stk];
      return val !== undefined ? val : null as any;
    });
  });

  // Calculate dynamic interpretation parameters
  const nearExpiry = expiries[0];
  const farExpiry = expiries[expiries.length - 1];
  const nearIvAvg = data.points
    .filter((p) => p.expiry_date === nearExpiry)
    .reduce((sum, p) => sum + p.computed_iv, 0) / (data.points.filter((p) => p.expiry_date === nearExpiry).length || 1);
  const farIvAvg = data.points
    .filter((p) => p.expiry_date === farExpiry)
    .reduce((sum, p) => sum + p.computed_iv, 0) / (data.points.filter((p) => p.expiry_date === farExpiry).length || 1);

  const atmStrike = strikes.reduce((prev, curr) =>
    Math.abs(curr - data.underlying_value) < Math.abs(prev - data.underlying_value) ? curr : prev
  );
  const lowStrike = strikes[0];
  const highStrike = strikes[strikes.length - 1];

  const lowStrikeIv = data.points.find((p) => p.strike === lowStrike)?.computed_iv || 0;
  const highStrikeIv = data.points.find((p) => p.strike === highStrike)?.computed_iv || 0;

  const isUpwardSloping = farIvAvg >= nearIvAvg;
  const hasPutSkew = lowStrikeIv > highStrikeIv;

  return (
    <div className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900/80 p-6 shadow-xl backdrop-blur-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-zinc-800 pb-4">
        <div>
          <h3 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
            Volatility Surface (3D)
            <span className="text-xs font-normal text-zinc-400 bg-zinc-800 px-2.5 py-0.5 rounded-full border border-zinc-700">
              {symbol} Multi-Expiry
            </span>
          </h3>
          <p className="text-sm text-zinc-400 mt-1">
            3D visualization of implied volatility across strike prices and expiry dates.
          </p>
        </div>
        <div className="text-xs text-zinc-400 bg-zinc-800/60 px-3 py-1.5 rounded-md border border-zinc-800 flex items-center gap-2 self-start sm:self-auto">
          <span>Points: {data.filtered_points_count} ({data.distinct_strikes_count} strikes × {data.distinct_expiries_count} expiries)</span>
        </div>
      </div>

      {/* Prominent Simulated Data Banner */}
      <div
        id="simulated-data-banner"
        className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-200 flex items-start space-x-3 shadow-inner"
      >
        <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-sm leading-relaxed">
          <span className="font-semibold text-amber-300 uppercase tracking-wide mr-2 bg-amber-500/20 px-2 py-0.5 rounded text-xs">
            Simulated Multi-Expiry Data
          </span>
          Multi-expiry surface data is simulated due to NSE live API access restrictions (403). The 2D IV smile above displays single-expiry market snapshot data.
        </div>
      </div>

      {/* 3D Plot Container */}
      <div className="relative w-full rounded-lg border border-zinc-800/80 bg-zinc-950/90 overflow-hidden flex justify-center">
        <Plot
          data={[
            {
              type: 'surface',
              x: strikes,
              y: yLabels,
              z: zMatrix,
              colorscale: 'Viridis',
              colorbar: {
                title: 'IV (%)',
                titleside: 'top',
                tickfont: { color: '#a1a1aa' },
                titlefont: { color: '#f4f4f5', size: 12 },
              },
              contours: {
                z: { show: true, usecolormap: true, highlightcolor: '#4ade80', project: { z: true } },
              },
              hovertemplate:
                '<b>Strike:</b> ₹%{x}<br>' +
                '<b>Expiry:</b> %{y}<br>' +
                '<b>Implied Volatility:</b> %{z:.2f}%<extra></extra>',
            },
          ]}
          layout={{
            autosize: true,
            margin: { l: 20, r: 20, b: 30, t: 30 },
            paper_bgcolor: '#09090b',
            plot_bgcolor: '#09090b',
            scene: {
              xaxis: {
                title: { text: 'Strike Price (₹)', font: { color: '#f4f4f5', size: 12 } },
                tickfont: { color: '#a1a1aa', size: 10 },
                gridcolor: '#27272a',
                zerolinecolor: '#3f3f46',
                backgroundcolor: '#09090b',
              },
              yaxis: {
                title: { text: 'Expiry Date', font: { color: '#f4f4f5', size: 12 } },
                tickfont: { color: '#a1a1aa', size: 10 },
                gridcolor: '#27272a',
                zerolinecolor: '#3f3f46',
                backgroundcolor: '#09090b',
              },
              zaxis: {
                title: { text: 'Implied Volatility (%)', font: { color: '#f4f4f5', size: 12 } },
                tickfont: { color: '#a1a1aa', size: 10 },
                gridcolor: '#27272a',
                zerolinecolor: '#3f3f46',
                backgroundcolor: '#09090b',
              },
              camera: {
                eye: { x: 1.6, y: -1.6, z: 1.2 },
              },
            },
          }}
          useResizeHandler={true}
          className="w-full h-[480px]"
          config={{ responsive: true, displayModeBar: true, displaylogo: false }}
        />
      </div>

      {/* Dynamic Plain-Language Interpretation Note */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4 space-y-2">
        <div className="flex items-center space-x-2 text-blue-400 font-medium text-sm">
          <Info className="h-4 w-4" />
          <span>Surface Structure Interpretation (Simulated Model)</span>
        </div>
        <p className="text-sm text-zinc-300 leading-relaxed">
          {isUpwardSloping ? (
            <>
              <strong>Term Structure:</strong> Implied volatility exhibits an upward-sloping term structure (
              {nearIvAvg.toFixed(1)}% at near expiry vs {farIvAvg.toFixed(1)}% at far expiry), typical of calm market conditions where longer-dated options command higher volatility risk premiums.
            </>
          ) : (
            <>
              <strong>Term Structure:</strong> Implied volatility exhibits an inverted term structure (
              {nearIvAvg.toFixed(1)}% at near expiry vs {farIvAvg.toFixed(1)}% at far expiry), typical of elevated short-term uncertainty or upcoming catalyst events.
            </>
          )}
        </p>
        <p className="text-sm text-zinc-300 leading-relaxed">
          {hasPutSkew ? (
            <>
              <strong>Volatility Skew:</strong> Displays a characteristic equity index put skew where lower strike put options (₹{lowStrike} IV: {lowStrikeIv.toFixed(1)}%) carry higher implied volatility than higher strike call options (₹{highStrike} IV: {highStrikeIv.toFixed(1)}%), reflecting market demand for downside protection.
            </>
          ) : (
            <>
              <strong>Volatility Skew:</strong> Displays a call-dominated skew across strikes (₹{lowStrike} IV: {lowStrikeIv.toFixed(1)}% vs ₹{highStrike} IV: {highStrikeIv.toFixed(1)}%).
            </>
          )}
        </p>
        <p className="text-xs text-zinc-400 pt-1 border-t border-zinc-800/80">
          <em>Note: This 3D surface illustrates standard theoretical term structure and skew dynamics using simulated multi-expiry quotes (due to NSE API access restrictions). Individual IV points are solved via the project's exact Black-Scholes solver.</em>
        </p>
      </div>
    </div>
  );
};
