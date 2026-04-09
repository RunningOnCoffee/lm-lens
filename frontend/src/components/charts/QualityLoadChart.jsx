import { useMemo } from 'react';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';
import InfoTip from '../InfoTip';

function formatElapsed(seconds) {
  if (seconds == null) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

/**
 * Quality-under-load correlation chart.
 * Shows cumulative quality flag rate over time, overlaid with active users.
 * Only render when snapshots contain quality flags.
 */
export default function QualityLoadChart({ snapshots }) {
  const { data, hasFlags } = useMemo(() => {
    let cumulativeFlags = 0;
    let cumulativeCompleted = 0;

    const points = snapshots.map((s) => {
      cumulativeFlags += s.quality_flag_count || 0;
      // Use completed_requests as a running total from the snapshot
      const completedThisWindow = s.completed_requests || 0;
      // For historical snapshots, completed_requests is cumulative
      // For live snapshots, it's also cumulative
      // We need per-window completed to compute rate, but cumulative flag rate is smoother
      // Use the cumulative completed from the snapshot directly
      const totalCompleted = completedThisWindow;

      return {
        time: s.elapsed_seconds ?? 0,
        flagRate: totalCompleted > 0 ? (cumulativeFlags / totalCompleted) * 100 : 0,
        windowFlags: s.quality_flag_count || 0,
        users: s.active_users,
      };
    });

    return {
      data: points,
      hasFlags: cumulativeFlags > 0,
    };
  }, [snapshots]);

  if (!hasFlags) return null;

  const maxRate = Math.max(...data.map((d) => d.flagRate));
  const yMax = Math.max(5, Math.ceil(maxRate / 5) * 5); // Round up to nearest 5%

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3 inline-flex items-center gap-1.5">
        Quality Under Load
        <InfoTip text="Shows how response quality degrades as load increases. The line tracks the cumulative percentage of responses with quality flags (truncated, empty, refusal, format issues, etc.) over time, overlaid with the number of active users." />
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
            yAxisId="rate"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
            domain={[0, yMax]}
            width={45}
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
              if (name === 'flagRate') return [`${value.toFixed(2)}%`, 'Flag Rate'];
              return [value, name];
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
            yAxisId="rate"
            dataKey="flagRate"
            name="flagRate"
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
