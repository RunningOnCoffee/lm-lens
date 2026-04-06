import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE, PROFILE_COLORS } from './ChartTheme';
import InfoTip from '../InfoTip';

const FLAG_COLORS = {
  truncated: 'text-warn',
  empty: 'text-gray-400',
  refusal: 'text-danger',
  repeated_tokens: 'text-purple-400',
};

export default function ProfileComparison({ profileStats }) {
  if (!profileStats || profileStats.length === 0) {
    return (
      <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
        <h3 className="font-heading text-sm font-semibold text-gray-300 mb-4">
          Per-Profile Performance
        </h3>
        <div className="h-48 flex items-center justify-center text-gray-600 text-sm">
          No profile data available
        </div>
      </div>
    );
  }

  const chartData = profileStats.map((p) => ({
    name: p.profile_name,
    ttft_p50: p.ttft_p50,
    ttft_p95: p.ttft_p95,
  }));

  const fmt = (v) => v != null ? v.toFixed(1) : '-';

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="font-heading text-sm font-semibold text-gray-300 mb-4">
        Per-Profile Performance
      </h3>

      {/* Chart: TTFT p50/p95 per profile */}
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} barCategoryGap="20%">
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis dataKey="name" tick={AXIS_STYLE} />
          <YAxis
            tick={AXIS_STYLE}
            width={50}
            label={{ value: 'TTFT (ms)', angle: -90, position: 'insideLeft', style: { ...AXIS_STYLE, fill: '#4b5563' } }}
          />
          <Tooltip
            {...TOOLTIP_STYLE}
            formatter={(value, name) => [`${value?.toFixed(1)} ms`, name === 'ttft_p50' ? 'P50 TTFT' : 'P95 TTFT']}
          />
          <Legend
            formatter={(value) => value === 'ttft_p50' ? 'P50 TTFT' : 'P95 TTFT'}
            wrapperStyle={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
          />
          <Bar dataKey="ttft_p50" fill={COLORS.accent} radius={[2, 2, 0, 0]} />
          <Bar dataKey="ttft_p95" fill={COLORS.warn} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Stats table */}
      <div className="mt-4">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-surface-600">
              <th className="text-left py-2 px-2 text-gray-500 font-semibold">Profile</th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">Requests</th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">Error %</th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">
                <span className="inline-flex items-center gap-1">TTFT P50 <InfoTip text="Median Time to First Token — how long until the model starts responding. Lower is better." /></span>
              </th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">
                <span className="inline-flex items-center gap-1">TTFT P95 <InfoTip text="95th percentile Time to First Token — only 5% of requests are slower than this value." /></span>
              </th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">
                <span className="inline-flex items-center gap-1">tok/s P50 <InfoTip text="Median tokens per second — how fast the model generates text. Higher is better." /></span>
              </th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">
                <span className="inline-flex items-center gap-1">tok/s P5 <InfoTip text="5th percentile tokens per second — the slowest 5% of requests. Shows worst-case generation speed." /></span>
              </th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">Avg Tokens</th>
              <th className="text-left py-2 px-2 text-gray-500 font-semibold">
                <span className="inline-flex items-center gap-1">Flags <InfoTip text="Quality flags detected in responses: truncated (hit token limit), empty (no output), refusal (model declined), repeated (degenerate repetition)." /></span>
              </th>
            </tr>
          </thead>
          <tbody>
            {profileStats.map((p, i) => {
              const errorPct = p.total_requests > 0
                ? ((p.fail_count / p.total_requests) * 100).toFixed(1)
                : '0.0';
              const flagEntries = Object.entries(p.quality_flag_counts || {}).filter(([, v]) => v > 0);

              return (
                <tr
                  key={p.profile_id}
                  className="border-b border-surface-600/50 last:border-b-0"
                >
                  <td className="py-2 px-2 text-gray-200">
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-1.5"
                      style={{ backgroundColor: PROFILE_COLORS[i % PROFILE_COLORS.length] }}
                    />
                    {p.profile_name}
                  </td>
                  <td className="text-right py-2 px-2 text-gray-300">{p.total_requests}</td>
                  <td className={`text-right py-2 px-2 ${p.fail_count > 0 ? 'text-danger' : 'text-gray-400'}`}>
                    {errorPct}%
                  </td>
                  <td className="text-right py-2 px-2 text-gray-300">{fmt(p.ttft_p50)}</td>
                  <td className="text-right py-2 px-2 text-gray-300">{fmt(p.ttft_p95)}</td>
                  <td className="text-right py-2 px-2 text-gray-300">{fmt(p.tps_p50)}</td>
                  <td className="text-right py-2 px-2 text-gray-300">{fmt(p.tps_p5)}</td>
                  <td className="text-right py-2 px-2 text-gray-300">{fmt(p.avg_output_tokens)}</td>
                  <td className="py-2 px-2">
                    {flagEntries.length > 0 ? (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {flagEntries.map(([flag, count]) => (
                          <span key={flag} className={`${FLAG_COLORS[flag] || 'text-gray-400'}`}>
                            {flag}:{count}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-600">-</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
