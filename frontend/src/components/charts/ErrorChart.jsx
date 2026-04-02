import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';

function formatElapsed(seconds) {
  if (seconds == null) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

export default function ErrorChart({ snapshots }) {
  const data = snapshots.map((s) => {
    const total = (s.completed_requests || 0) + (s.failed_requests || 0);
    return {
      time: s.elapsed_seconds ?? 0,
      errors: s.error_count || 0,
      errorRate: total > 0 ? ((s.failed_requests || 0) / total) * 100 : 0,
      failed: s.failed_requests || 0,
    };
  });

  const hasErrors = data.some((d) => d.errors > 0 || d.failed > 0);

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">
        Errors Over Time
      </h3>
      {!hasErrors ? (
        <div className="flex items-center justify-center h-[240px] text-sm text-green-400/60">
          No errors recorded
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis
              dataKey="time"
              tickFormatter={formatElapsed}
              tick={AXIS_STYLE}
              axisLine={{ stroke: COLORS.surface600 }}
              tickLine={false}
            />
            <YAxis
              tick={AXIS_STYLE}
              axisLine={false}
              tickLine={false}
              width={35}
              allowDecimals={false}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              labelFormatter={(v) => `t = ${formatElapsed(v)}`}
              formatter={(value, name) => {
                if (name === 'errorRate') return [`${value.toFixed(1)}%`, 'Error Rate'];
                if (name === 'errors') return [value, 'Errors (window)'];
                return [value, name];
              }}
            />
            <Area
              dataKey="errors"
              name="errors"
              fill={COLORS.danger}
              stroke={COLORS.danger}
              strokeWidth={2}
              fillOpacity={0.2}
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
