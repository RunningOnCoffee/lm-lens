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

export default function ThroughputChart({ snapshots }) {
  const data = snapshots.map((s) => ({
    time: s.elapsed_seconds ?? 0,
    tps: s.throughput_tps,
    rps: s.throughput_rps,
  }));

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3 inline-flex items-center gap-1.5">
        Throughput Over Time
        <InfoTip text="Tokens per second (generation speed) and requests per second over time. Higher throughput means the endpoint is handling more work." />
      </h3>
      {data.length === 0 ? (
        <div className="h-[240px] flex items-center justify-center text-gray-600 text-xs">
          No throughput data yet. Data will appear as the benchmark runs.
        </div>
      ) : (
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
            yAxisId="tps"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}`}
            width={40}
            label={{ value: 'tok/s', angle: -90, position: 'insideLeft', style: { ...AXIS_STYLE, fill: COLORS.gray600 }, offset: 10 }}
          />
          <YAxis
            yAxisId="rps"
            orientation="right"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}`}
            width={35}
            label={{ value: 'req/s', angle: 90, position: 'insideRight', style: { ...AXIS_STYLE, fill: COLORS.gray600 }, offset: 10 }}
          />
          <Tooltip
            {...TOOLTIP_STYLE}
            labelFormatter={(v) => `t = ${formatElapsed(v)}`}
            formatter={(value, name) => {
              if (value == null) return ['-', name];
              const labels = { tps: 'Tokens/s', rps: 'Requests/s' };
              return [`${value.toFixed(1)}`, labels[name] || name];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
          />
          <Area
            yAxisId="tps"
            dataKey="tps"
            name="tps"
            fill={COLORS.accent}
            stroke={COLORS.accent}
            strokeWidth={2}
            fillOpacity={0.15}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            yAxisId="rps"
            dataKey="rps"
            name="rps"
            stroke={COLORS.green}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      )}
    </div>
  );
}
