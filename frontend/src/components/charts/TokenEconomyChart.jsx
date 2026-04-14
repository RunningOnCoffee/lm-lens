import { useState, useEffect } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';
import { dashboardApi } from '../../api/client';
import InfoTip from '../InfoTip';

function formatTokens(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function TokenEconomyChart() {
  const [groupBy, setGroupBy] = useState('profile');
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    dashboardApi.tokenEconomy({ group_by: groupBy })
      .then((res) => setData(res.data || []))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [groupBy]);

  const chartData = data.map((d) => ({
    name: d.group_name.length > 18 ? d.group_name.slice(0, 16) + '...' : d.group_name,
    fullName: d.group_name,
    input: d.total_input_tokens,
    output: d.total_output_tokens,
  }));

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold inline-flex items-center gap-1.5">
          Token Economy
          <InfoTip text="Input vs output tokens across all completed benchmarks. Switch between grouping by endpoint or user profile to compare token consumption patterns." />
        </h3>
        <div className="flex bg-surface-700 rounded-lg p-0.5">
          <button
            onClick={() => setGroupBy('profile')}
            className={`px-2.5 py-1 text-[10px] rounded-md transition-colors ${
              groupBy === 'profile' ? 'bg-accent/20 text-accent font-medium' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            By Profile
          </button>
          <button
            onClick={() => setGroupBy('endpoint')}
            className={`px-2.5 py-1 text-[10px] rounded-md transition-colors ${
              groupBy === 'endpoint' ? 'bg-accent/20 text-accent font-medium' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            By Endpoint
          </button>
        </div>
      </div>

      {loading && <div className="h-[240px] flex items-center justify-center text-gray-600 text-xs">Loading...</div>}

      {!loading && chartData.length === 0 && (
        <div className="h-[240px] flex items-center justify-center text-gray-600 text-xs">No token data available</div>
      )}

      {!loading && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="name" tick={AXIS_STYLE} axisLine={{ stroke: COLORS.surface600 }} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={50} tickFormatter={formatTokens} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(value, name) => [formatTokens(value), name === 'Input' ? 'Input Tokens' : 'Output Tokens']}
              labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
            />
            <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} />
            <Bar dataKey="input" name="Input" fill={COLORS.accent} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="output" name="Output" fill={COLORS.purple} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
