import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';
import { useMemo } from 'react';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';

export default function ProfileBreakdown({ snapshots }) {
  // Aggregate per_profile across recent snapshots for stability
  const data = useMemo(() => {
    if (!snapshots.length) return [];

    // Aggregate the last 10 snapshots for more stable per-profile data
    const recent = snapshots.slice(-10);
    const agg = {};

    for (const snap of recent) {
      if (!snap?.per_profile) continue;
      for (const [name, stats] of Object.entries(snap.per_profile)) {
        if (!agg[name]) agg[name] = { ttft: [], tps: [], completed: 0 };
        if (stats.p50_ttft_ms != null) agg[name].ttft.push(stats.p50_ttft_ms);
        if (stats.avg_tps != null) agg[name].tps.push(stats.avg_tps);
        agg[name].completed += stats.completed || 0;
      }
    }

    return Object.entries(agg)
      .filter(([, v]) => v.completed > 0)
      .map(([name, v]) => ({
        name: name.length > 16 ? name.slice(0, 14) + '…' : name,
        fullName: name,
        p50_ttft: v.ttft.length ? v.ttft.reduce((a, b) => a + b, 0) / v.ttft.length : null,
        avg_tps: v.tps.length ? v.tps.reduce((a, b) => a + b, 0) / v.tps.length : null,
        requests: v.completed,
      }));
  }, [snapshots]);

  if (data.length === 0) {
    return (
      <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
        <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">
          Per-Profile Breakdown
        </h3>
        <div className="flex items-center justify-center h-[200px] text-sm text-gray-600">
          Waiting for per-profile data...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">
        Per-Profile Performance
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid {...GRID_STYLE} />
          <XAxis
            dataKey="name"
            tick={{ ...AXIS_STYLE, fontSize: 9 }}
            axisLine={{ stroke: '#252a3a' }}
            tickLine={false}
            interval={0}
          />
          <YAxis
            yAxisId="ms"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => v >= 10000 ? `${(v / 1000).toFixed(0)}s` : `${v}ms`}
            width={50}
          />
          <YAxis
            yAxisId="tps"
            orientation="right"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}`}
            width={35}
          />
          <Tooltip
            {...TOOLTIP_STYLE}
            formatter={(value, name) => {
              if (value == null) return ['-', name];
              if (name === 'p50_ttft') {
                return [value >= 10000 ? `${(value / 1000).toFixed(2)}s` : `${value.toFixed(0)}ms`, 'P50 TTFT'];
              }
              if (name === 'avg_tps') return [`${value.toFixed(1)} tok/s`, 'Avg tok/s'];
              return [value, name];
            }}
            labelFormatter={(_, payload) => {
              const p = payload?.[0]?.payload;
              return p ? `${p.fullName} (${p.requests} reqs)` : '';
            }}
          />
          <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} />
          <Bar
            yAxisId="ms"
            dataKey="p50_ttft"
            name="p50_ttft"
            fill={COLORS.accent}
            fillOpacity={0.7}
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
          <Line
            yAxisId="tps"
            dataKey="avg_tps"
            name="avg_tps"
            stroke={COLORS.green}
            strokeWidth={2}
            dot={{ fill: COLORS.green, r: 4 }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
