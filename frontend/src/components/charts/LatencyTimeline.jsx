import { useMemo } from 'react';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';

function formatElapsed(seconds) {
  if (seconds == null) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

/**
 * Compute a simple moving average over a window of `size` points.
 * Skips null values — only averages available data in each window.
 */
function movingAverage(values, size) {
  return values.map((_, i) => {
    const start = Math.max(0, i - size + 1);
    const window = values.slice(start, i + 1).filter((v) => v != null);
    return window.length > 0 ? window.reduce((a, b) => a + b, 0) / window.length : null;
  });
}

export default function LatencyTimeline({ snapshots }) {
  const data = useMemo(() => {
    // Check if we have rolling data (live WebSocket) or per-window data (historical)
    const hasRolling = snapshots.some((s) => s.rolling_p50_ttft_t1_ms != null);

    if (hasRolling) {
      // Live data — use rolling 30s first-turn TTFT
      return snapshots.map((s) => ({
        time: s.elapsed_seconds ?? 0,
        p50: s.rolling_p50_ttft_t1_ms,
        p95: s.rolling_p95_ttft_t1_ms,
        users: s.active_users,
      }));
    }

    // Historical data — smooth per-window values with moving average
    const WINDOW = 10; // 10-second moving average
    const rawP50 = snapshots.map((s) => s.p50_ttft_ms);
    const rawP95 = snapshots.map((s) => s.p95_ttft_ms);
    const smoothP50 = movingAverage(rawP50, WINDOW);
    const smoothP95 = movingAverage(rawP95, WINDOW);

    return snapshots.map((s, i) => ({
      time: s.elapsed_seconds ?? 0,
      p50: smoothP50[i],
      p95: smoothP95[i],
      users: s.active_users,
    }));
  }, [snapshots]);

  // Determine sensible Y-axis formatting based on data range
  const maxMs = Math.max(...data.map((d) => d.p95 ?? d.p50 ?? 0).filter(Boolean));
  const formatMs = (v) => {
    if (maxMs > 10000) return `${(v / 1000).toFixed(1)}s`;
    return `${v.toFixed(0)}ms`;
  };

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">
        First-Turn TTFT Over Time
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid {...GRID_STYLE} />
          <XAxis
            dataKey="time"
            tickFormatter={formatElapsed}
            tick={AXIS_STYLE}
            axisLine={{ stroke: COLORS.surface600 }}
            tickLine={false}
          />
          <YAxis
            yAxisId="ms"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatMs}
            width={55}
          />
          <YAxis
            yAxisId="users"
            orientation="right"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            width={35}
          />
          <Tooltip
            {...TOOLTIP_STYLE}
            labelFormatter={(v) => `t = ${formatElapsed(v)}`}
            formatter={(value, name) => {
              if (name === 'users') return [value, 'Active Users'];
              if (value == null) return ['-', name];
              const label = name === 'p50' ? 'P50 TTFT' : 'P95 TTFT';
              return [value >= 10000 ? `${(value / 1000).toFixed(2)}s` : `${value.toFixed(0)}ms`, label];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
          />
          <Area
            yAxisId="users"
            dataKey="users"
            name="users"
            fill={COLORS.surface700}
            stroke={COLORS.gray500}
            strokeWidth={1}
            fillOpacity={0.4}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            yAxisId="ms"
            dataKey="p50"
            name="p50"
            stroke={COLORS.accent}
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            yAxisId="ms"
            dataKey="p95"
            name="p95"
            stroke={COLORS.warn}
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
