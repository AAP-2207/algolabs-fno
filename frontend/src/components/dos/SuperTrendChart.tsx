import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, TrendingDown, Clock } from 'lucide-react'

export interface CandleData {
  time: string
  open: number
  high: number
  low: number
  close: number
  supertrend: number
  trend: 'up' | 'down' | string
}

export interface SuperTrendSignalPanelProps {
  candleData: CandleData[]
  currentTrend: 'up' | 'down' | string
  lastUpdated: string
}

export function SuperTrendSignalPanel({
  candleData,
  currentTrend,
  lastUpdated,
}: SuperTrendSignalPanelProps) {
  const [timeLeft, setTimeLeft] = useState<string>('05:00')
  const [formattedTime, setFormattedTime] = useState<string>('')

  // Countdown timer for 5-minute candle
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date()
      const seconds = now.getSeconds()
      const milliseconds = now.getMilliseconds()

      // Calculate time until next 5-minute mark
      const currentMinutes = now.getMinutes()
      const nextCandleMinute =
        Math.ceil((currentMinutes + 1) / 5) * 5
      const minutesDiff =
        nextCandleMinute > 59
          ? 5 - (currentMinutes % 5)
          : Math.ceil((nextCandleMinute - currentMinutes) * 60 - seconds) / 60

      const remainingSeconds = Math.round(
        (minutesDiff % 1) * 60 - (milliseconds / 1000)
      )
      const remainingMinutes = Math.floor(minutesDiff)

      const displaySeconds = remainingSeconds < 0 ? 59 : remainingSeconds
      const displayMinutes =
        remainingSeconds < 0 ? remainingMinutes - 1 : remainingMinutes

      setTimeLeft(
        `${String(displayMinutes).padStart(2, '0')}:${String(displaySeconds).padStart(2, '0')}`
      )
    }, 100)

    return () => clearInterval(interval)
  }, [])

  // Format last updated timestamp
  useEffect(() => {
    if (!lastUpdated) return
    const date = new Date(lastUpdated)
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    setFormattedTime(`${hours}:${minutes}:${seconds}`)
  }, [lastUpdated])

  const isUptrend = currentTrend === 'up'
  const trendBgColor = isUptrend
    ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-500/50'
    : 'bg-gradient-to-r from-red-500/20 to-rose-500/20 border-red-500/50'

  const trendTextColor = isUptrend ? 'text-green-400' : 'text-red-400'
  const trendLabel = isUptrend ? 'UPTREND — Sell CE' : 'DOWNTREND — Sell PE'
  const TrendIcon = isUptrend ? TrendingUp : TrendingDown

  // Custom tooltip for the chart
  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean
    payload?: Array<{
      value: number
      name: string
      payload: CandleData
    }>
  }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-card/95 border border-border rounded-lg p-3 shadow-lg backdrop-blur-sm">
          <p className="text-foreground text-sm font-semibold">{data.time}</p>
          <p className="text-primary text-xs mt-1">
            Close: ₹{data.close.toFixed(2)}
          </p>
          <p className="text-muted-foreground text-xs">
            High: ₹{data.high.toFixed(2)} | Low: ₹{data.low.toFixed(2)}
          </p>
          <p className="text-destructive text-xs mt-1">
            SuperTrend: ₹{data.supertrend.toFixed(2)}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full bg-card border border-border rounded-xl p-6 shadow-2xl">
      {/* Header with Trend Badge and Timer */}
      <div className="flex items-center justify-between mb-6">
        <div>
          {/* Trend Badge */}
          <div
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${trendBgColor} backdrop-blur-sm`}
          >
            <TrendIcon className={`w-5 h-5 ${trendTextColor}`} />
            <span className={`font-bold text-sm ${trendTextColor}`}>
              {trendLabel}
            </span>
          </div>
        </div>

        {/* Timer and Last Updated */}
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2 bg-muted/40 px-3 py-1.5 rounded-lg border border-border/50">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-mono font-semibold text-primary">
              {timeLeft}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Updated: {formattedTime}
          </p>
        </div>
      </div>

      {/* Chart Container */}
      <div className="w-full h-96 bg-background/50 rounded-lg border border-border/30 p-4">
        {candleData && candleData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={candleData}>
              <defs>
                {/* Gradient for uptrend */}
                <linearGradient
                  id="supertrendUpGradient"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor="rgb(34, 197, 94)" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="rgb(34, 197, 94)" stopOpacity={0} />
                </linearGradient>
                {/* Gradient for downtrend */}
                <linearGradient
                  id="supertrendDownGradient"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor="rgb(239, 68, 68)" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="rgb(239, 68, 68)" stopOpacity={0} />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.05)"
              />
              <XAxis
                dataKey="time"
                stroke="rgba(255,255,255,0.3)"
                tick={{ fontSize: 12 }}
                interval={Math.max(0, Math.floor(candleData.length / 8))}
              />
              <YAxis
                stroke="rgba(255,255,255,0.3)"
                tick={{ fontSize: 12 }}
                domain={['dataMin - 50', 'dataMax + 50']}
                tickFormatter={(value) => Math.round(value).toLocaleString()}
                width={70}
              />
              <Tooltip content={<CustomTooltip />} />

              {/* Close Price Line */}
              <Line
                type="monotone"
                dataKey="close"
                stroke="rgb(147, 197, 253)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                name="Price"
              />

              {/* SuperTrend Line - Dynamic Color */}
              <Line
                type="stepAfter"
                dataKey="supertrend"
                stroke={isUptrend ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'}
                strokeWidth={3}
                dot={false}
                isAnimationActive={false}
                name="SuperTrend"
                strokeDasharray="0"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <p className="text-muted-foreground text-sm">No data available</p>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex gap-6 mt-6 px-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-blue-400 rounded" />
          <span className="text-xs text-muted-foreground">Price (Close)</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-0.5 rounded ${isUptrend ? 'bg-green-500' : 'bg-red-500'}`}
          />
          <span className="text-xs text-muted-foreground">SuperTrend</span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <div className="w-2 h-2 rounded-full bg-primary" />
          <span className="text-xs text-muted-foreground">
            Bank Nifty • 5m
          </span>
        </div>
      </div>
    </div>
  )
}
