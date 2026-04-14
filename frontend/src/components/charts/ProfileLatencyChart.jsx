import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { COLORS, PROFILE_COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';
import InfoTip from '../InfoTip';

export default function ProfileLatencyChart({ profiles }) {
  if (!profiles || profiles.length === 0) return null;

  const data = profiles
    .filter((p) => p.avg_ttft_p50 != null)
    .map((p) => ({
      name: p.profile_name,
      ttft: Math.round(p.avg_ttft_p50 || 0),
      benchmarks: p.benchmark_count,
    }))
    .sort((a, b) => b.ttft - a.ttft);

  if (data.length === 0) return null;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3 inline-flex items-center gap-1.5">
        TTFT by Profile
        <InfoTip text="Average Time to First Token (p50) per user profile across all endpoints. Shows which workload types are fastest/slowest." />
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid {...GRID_STYLE} />
          <XAxis type="number" tick={AXIS_STYLE} axisLine={{ stroke: COLORS.surface600 }} tickLine={false} tickFormatter={(v) => `${v}ms`} />
          <YAxis type="category" dataKey="name" tick={AXIS_STYLE} axisLine={false} tickLine={false} width={100} />
          <Tooltip
            {...TOOLTIP_STYLE}
            formatter={(value) => [`${value} ms`, 'TTFT p50']}
          />
          <Bar dataKey="ttft" fill={COLORS.warn} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
