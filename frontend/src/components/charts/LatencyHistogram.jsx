import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { benchmarksApi } from '../../api/client';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';
import InfoTip from '../InfoTip';
import Spinner from '../Spinner';

const METRICS = [
  { id: 'ttft_ms', label: 'TTFT (ms)' },
  { id: 'tgt_ms', label: 'TGT (ms)' },
  { id: 'tokens_per_second', label: 'Tokens/sec' },
];

export default function LatencyHistogram({ benchmarkId, profiles }) {
  const [metric, setMetric] = useState('ttft_ms');
  const [profileFilter, setProfileFilter] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = { metric, bins: 30 };
    if (profileFilter) params.profile_id = profileFilter;

    benchmarksApi.histogram(benchmarkId, params).then((res) => {
      if (!cancelled) {
        setData(res.data);
        setLoading(false);
      }
    }).catch(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [benchmarkId, metric, profileFilter]);

  const bins = data?.bins || [];
  const stats = data?.stats || {};
  const metricLabel = METRICS.find((m) => m.id === metric)?.label || metric;

  // Format bin labels for x-axis
  const chartData = bins.map((b, i) => ({
    name: b.min.toFixed(0),
    count: b.count,
    range: `${b.min.toFixed(1)} - ${b.max.toFixed(1)}`,
    idx: i,
  }));

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-heading text-sm font-semibold text-gray-300 inline-flex items-center gap-1.5">
          Latency Distribution
          <InfoTip text="Shows how request latencies are distributed. A narrow, left-leaning distribution means consistent fast responses. A long right tail indicates occasional slow requests. The colored lines mark P50 (median), P95, and P99 percentiles." />
        </h3>
        <div className="flex items-center gap-2">
          {profiles && profiles.length > 1 && (
            <select
              value={profileFilter}
              onChange={(e) => setProfileFilter(e.target.value)}
              className="input text-xs py-1 px-2"
            >
              <option value="">All Profiles</option>
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.profile_name}
                </option>
              ))}
            </select>
          )}
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="input text-xs py-1 px-2"
          >
            {METRICS.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="h-64 flex items-center justify-center gap-2 text-gray-600 text-sm">
          <Spinner size="sm" /> Loading histogram...
        </div>
      ) : chartData.length === 0 ? (
        <div className="h-64 flex items-center justify-center text-gray-600 text-sm">
          No data available
        </div>
      ) : (
        <>
          {/* Stats row */}
          <div className="flex items-center gap-4 mb-3 text-[11px] font-mono">
            {stats.p50 != null && (
              <span className="text-gray-400 inline-flex items-center gap-1">
                <span>P50: <span className="text-accent">{stats.p50.toFixed(1)}</span></span>
                <InfoTip text="Median — 50% of requests are faster than this value." />
              </span>
            )}
            {stats.p95 != null && (
              <span className="text-gray-400 inline-flex items-center gap-1">
                <span>P95: <span className="text-warn">{stats.p95.toFixed(1)}</span></span>
                <InfoTip text="95th percentile — only 5% of requests are slower." />
              </span>
            )}
            {stats.p99 != null && (
              <span className="text-gray-400 inline-flex items-center gap-1">
                <span>P99: <span className="text-danger">{stats.p99.toFixed(1)}</span></span>
                <InfoTip text="99th percentile — only 1% of requests are slower. Shows worst-case behavior." />
              </span>
            )}
            {stats.mean != null && (
              <span className="text-gray-400">
                Mean: <span className="text-gray-300">{stats.mean.toFixed(1)}</span>
              </span>
            )}
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} barCategoryGap="1%">
              <CartesianGrid {...GRID_STYLE} vertical={false} />
              <XAxis
                dataKey="name"
                tick={AXIS_STYLE}
                interval={Math.max(0, Math.floor(chartData.length / 8) - 1)}
                label={{ value: metricLabel, position: 'insideBottom', offset: -5, style: { ...AXIS_STYLE, fill: '#4b5563' } }}
              />
              <YAxis tick={AXIS_STYLE} width={40} />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(value) => [value, 'Requests']}
                labelFormatter={(_, payload) => payload[0]?.payload?.range || ''}
              />
              <Bar dataKey="count" fill={COLORS.accent} radius={[2, 2, 0, 0]} />
              {stats.p50 != null && (
                <ReferenceLine
                  x={_closestBin(chartData, stats.p50)}
                  stroke={COLORS.accent}
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                />
              )}
              {stats.p95 != null && (
                <ReferenceLine
                  x={_closestBin(chartData, stats.p95)}
                  stroke={COLORS.warn}
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                />
              )}
              {stats.p99 != null && (
                <ReferenceLine
                  x={_closestBin(chartData, stats.p99)}
                  stroke={COLORS.danger}
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                />
              )}
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}

function _closestBin(chartData, value) {
  let closest = chartData[0]?.name;
  let minDist = Infinity;
  for (const d of chartData) {
    const dist = Math.abs(parseFloat(d.name) - value);
    if (dist < minDist) {
      minDist = dist;
      closest = d.name;
    }
  }
  return closest;
}
