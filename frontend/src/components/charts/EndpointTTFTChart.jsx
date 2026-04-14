import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';
import InfoTip from '../InfoTip';

export default function EndpointTTFTChart({ endpoints }) {
  if (!endpoints || endpoints.length === 0) return null;

  const data = endpoints
    .filter((ep) => ep.avg_ttft_p50 != null)
    .map((ep) => ({
      name: ep.name.length > 18 ? ep.name.slice(0, 16) + '...' : ep.name,
      fullName: ep.name,
      p50: Math.round(ep.avg_ttft_p50 || 0),
    }));

  if (data.length === 0) return null;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3 inline-flex items-center gap-1.5">
        TTFT by Endpoint
        <InfoTip text="Average first-turn Time to First Token (p50) per endpoint across all runs. Lower is faster." />
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid {...GRID_STYLE} />
          <XAxis dataKey="name" tick={AXIS_STYLE} axisLine={{ stroke: COLORS.surface600 }} tickLine={false} />
          <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={50} tickFormatter={(v) => `${v}ms`} />
          <Tooltip
            {...TOOLTIP_STYLE}
            formatter={(value) => [`${value} ms`, 'TTFT p50']}
            labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
          />
          <Bar dataKey="p50" fill={COLORS.accent} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
