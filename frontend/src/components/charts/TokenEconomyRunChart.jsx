import { useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './ChartTheme';
import InfoTip from '../InfoTip';

function formatTokens(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatTime(ms) {
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(1)}s`;
  return `${ms.toFixed(0)}ms`;
}

function formatSpeed(v) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(0);
}

const VIEWS = [
  { id: 'tokens', label: 'Tokens' },
  { id: 'time', label: 'Time' },
  { id: 'speed', label: 'Speed' },
];

const VIEW_TIPS = {
  tokens: 'Input vs output tokens per user profile. High input/output ratio = prefill-heavy workload (e.g. RAG). Low ratio = decode-heavy (e.g. content generation).',
  time: 'GPU time spent in prefill (processing input context) vs decode (generating output tokens). Prefill is compute-bound; decode is memory-bandwidth-bound.',
  speed: 'Processing speed during each inference phase. Prefill tok/s = input tokens / TTFT. Decode tok/s = output tokens / (TGT - TTFT). Helps identify which phase is the bottleneck.',
};

export default function TokenEconomyRunChart({ profileStats }) {
  const [view, setView] = useState('tokens');

  if (!profileStats || profileStats.length === 0) return null;

  const hasTokenData = profileStats.some(
    (p) => (p.total_input_tokens || 0) + (p.total_output_tokens || 0) > 0
  );
  if (!hasTokenData) return null;

  const hasTimeData = profileStats.some(
    (p) => (p.total_prefill_ms || 0) + (p.total_decode_ms || 0) > 0
  );

  // Build chart data based on view
  let chartData, bar1, bar2, yFormatter, tooltipFormatter, labelFormatter, summaryLine;

  if (view === 'tokens') {
    chartData = profileStats.map((p) => ({
      name: truncName(p.profile_name),
      fullName: p.profile_name,
      a: p.total_input_tokens || 0,
      b: p.total_output_tokens || 0,
    }));
    const totalIn = chartData.reduce((s, d) => s + d.a, 0);
    const totalOut = chartData.reduce((s, d) => s + d.b, 0);
    bar1 = { key: 'a', name: 'Input', fill: COLORS.accent };
    bar2 = { key: 'b', name: 'Output', fill: COLORS.purple };
    yFormatter = formatTokens;
    tooltipFormatter = (value, name) => [formatTokens(value), name === 'Input' ? 'Input Tokens' : 'Output Tokens'];
    labelFormatter = (label, payload) => {
      const d = payload?.[0]?.payload;
      if (!d) return label;
      const total = d.a + d.b;
      const ratio = d.a > 0 ? (d.b / d.a).toFixed(2) : '-';
      return `${d.fullName} — ${formatTokens(total)} total (${ratio}x out/in)`;
    };
    summaryLine = (
      <>
        <span>In: <span className="text-accent">{formatTokens(totalIn)}</span></span>
        <span>Out: <span className="text-purple-400">{formatTokens(totalOut)}</span></span>
        <span>Ratio: <span className="text-gray-300">{totalIn > 0 ? (totalOut / totalIn).toFixed(2) : '-'}x</span></span>
      </>
    );
  } else if (view === 'time') {
    chartData = profileStats.map((p) => ({
      name: truncName(p.profile_name),
      fullName: p.profile_name,
      a: p.total_prefill_ms || 0,
      b: p.total_decode_ms || 0,
    }));
    const totalPrefill = chartData.reduce((s, d) => s + d.a, 0);
    const totalDecode = chartData.reduce((s, d) => s + d.b, 0);
    const totalTime = totalPrefill + totalDecode;
    bar1 = { key: 'a', name: 'Prefill', fill: COLORS.accent };
    bar2 = { key: 'b', name: 'Decode', fill: COLORS.purple };
    yFormatter = formatTime;
    tooltipFormatter = (value, name) => [formatTime(value), name === 'Prefill' ? 'Prefill Time' : 'Decode Time'];
    labelFormatter = (label, payload) => {
      const d = payload?.[0]?.payload;
      if (!d) return label;
      const total = d.a + d.b;
      const pct = total > 0 ? ((d.a / total) * 100).toFixed(0) : '-';
      return `${d.fullName} — ${formatTime(total)} total (${pct}% prefill)`;
    };
    summaryLine = (
      <>
        <span>Prefill: <span className="text-accent">{formatTime(totalPrefill)}</span></span>
        <span>Decode: <span className="text-purple-400">{formatTime(totalDecode)}</span></span>
        <span>Split: <span className="text-gray-300">{totalTime > 0 ? ((totalPrefill / totalTime) * 100).toFixed(0) : '-'}% prefill</span></span>
      </>
    );
  } else {
    // speed
    chartData = profileStats
      .filter((p) => p.prefill_tok_per_sec || p.decode_tok_per_sec)
      .map((p) => ({
        name: truncName(p.profile_name),
        fullName: p.profile_name,
        a: p.prefill_tok_per_sec || 0,
        b: p.decode_tok_per_sec || 0,
      }));
    bar1 = { key: 'a', name: 'Prefill', fill: COLORS.accent };
    bar2 = { key: 'b', name: 'Decode', fill: COLORS.purple };
    yFormatter = (v) => `${formatSpeed(v)}`;
    tooltipFormatter = (value, name) => [`${formatSpeed(value)} tok/s`, name === 'Prefill' ? 'Prefill Speed' : 'Decode Speed'];
    labelFormatter = (label, payload) => {
      const d = payload?.[0]?.payload;
      if (!d) return label;
      const ratio = d.b > 0 ? (d.a / d.b).toFixed(1) : '-';
      return `${d.fullName} — prefill ${ratio}x faster than decode`;
    };
    const avgPrefill = chartData.length > 0 ? chartData.reduce((s, d) => s + d.a, 0) / chartData.length : 0;
    const avgDecode = chartData.length > 0 ? chartData.reduce((s, d) => s + d.b, 0) / chartData.length : 0;
    summaryLine = (
      <>
        <span>Avg prefill: <span className="text-accent">{formatSpeed(avgPrefill)} tok/s</span></span>
        <span>Avg decode: <span className="text-purple-400">{formatSpeed(avgDecode)} tok/s</span></span>
      </>
    );
  }

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold inline-flex items-center gap-1.5">
          Token Economy
          <InfoTip text={VIEW_TIPS[view]} />
        </h3>
        <div className="flex items-center gap-3">
          <div className="flex bg-surface-700 rounded-lg p-0.5">
            {VIEWS.map((v) => (
              <button
                key={v.id}
                onClick={() => setView(v.id)}
                disabled={v.id !== 'tokens' && !hasTimeData}
                className={`px-2.5 py-1 text-[10px] rounded-md transition-colors ${
                  view === v.id
                    ? 'bg-accent/20 text-accent font-medium'
                    : !hasTimeData && v.id !== 'tokens'
                      ? 'text-gray-700 cursor-not-allowed'
                      : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 text-[10px] font-mono text-gray-500 mb-2">
        {summaryLine}
      </div>

      {chartData.length === 0 ? (
        <div className="h-[240px] flex items-center justify-center text-gray-600 text-xs">
          No data available for this view
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="name" tick={AXIS_STYLE} axisLine={{ stroke: COLORS.surface600 }} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} width={55} tickFormatter={yFormatter} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={tooltipFormatter}
              labelFormatter={labelFormatter}
            />
            <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} />
            <Bar dataKey={bar1.key} name={bar1.name} fill={bar1.fill} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <Bar dataKey={bar2.key} name={bar2.name} fill={bar2.fill} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function truncName(name) {
  return name.length > 18 ? name.slice(0, 16) + '...' : name;
}
