import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { benchmarksApi } from '../api/client';
import InfoTip from '../components/InfoTip';
import Spinner from '../components/Spinner';
import TabBar from '../components/TabBar';
import QualityFlagPill from '../components/QualityFlagPill';

const fmt = (v) => v != null ? v.toFixed(0) : '-';
const fmt1 = (v) => v != null ? v.toFixed(1) : '-';
const pct = (a, b) => {
  if (a == null || b == null || b === 0) return null;
  return ((a - b) / b) * 100;
};

function DeltaBadge({ value, invertColor }) {
  if (value == null) return null;
  const positive = value > 0;
  // For latency, higher is worse (red). For tok/s, higher is better (green).
  const isGood = invertColor ? positive : !positive;
  const color = Math.abs(value) < 1 ? 'text-gray-500' : isGood ? 'text-green-400' : 'text-danger';
  return (
    <span className={`text-[10px] font-mono ${color}`}>
      {positive ? '+' : ''}{value.toFixed(1)}%
    </span>
  );
}

export default function BenchmarkCompare() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [profilesA, setProfilesA] = useState(null);
  const [profilesB, setProfilesB] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('metrics');

  const idA = searchParams.get('a');
  const idB = searchParams.get('b');

  useEffect(() => {
    if (!idA || !idB) { setError('Two benchmark IDs required'); setLoading(false); return; }

    Promise.all([
      benchmarksApi.compare(idA, idB),
      benchmarksApi.profileStats(idA),
      benchmarksApi.profileStats(idB),
    ]).then(([cmp, psA, psB]) => {
      setData(cmp.data);
      setProfilesA(psA.data);
      setProfilesB(psB.data);
    }).catch((err) => {
      setError(err.message);
    }).finally(() => setLoading(false));
  }, [idA, idB]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 gap-2 text-gray-500 text-sm"><Spinner size="sm" /> Loading comparison...</div>;
  }
  if (error) {
    return (
      <div className="max-w-xl mx-auto mt-12">
        <div className="p-4 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">{error}</div>
        <button onClick={() => navigate('/benchmarks')} className="mt-4 text-sm text-accent hover:text-accent-bright">
          Back to Benchmarks
        </button>
      </div>
    );
  }

  const [benchA, benchB] = data.benchmarks;
  const sumA = benchA.results_summary || {};
  const sumB = benchB.results_summary || {};
  const epA = benchA.endpoint_snapshot || {};
  const epB = benchB.endpoint_snapshot || {};

  // Determine total sessions for the responses browser
  const totalSessions = Math.max(
    profilesA?.reduce((s, p) => s + p.total_requests, 0) || 0,
    profilesB?.reduce((s, p) => s + p.total_requests, 0) || 0,
  );

  // Matched seeds: same non-null seed AND same scenario → identical prompts
  const isMatchedSeed = benchA.seed != null && benchA.seed === benchB.seed
    && benchA.scenario_id === benchB.scenario_id;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button onClick={() => navigate('/benchmarks')} className="text-xs text-gray-500 hover:text-gray-300 mb-1 block">
          &larr; Back to Benchmarks
        </button>
        <h1 className="font-heading text-2xl font-bold">Benchmark Comparison</h1>
        {isMatchedSeed && (
          <span className="text-[11px] text-accent/70 mt-1 block">
            Seeded comparison — identical prompts across both runs
          </span>
        )}
      </div>

      {/* Run info */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <RunInfoCard label="A" benchmark={benchA} endpoint={epA} />
        <RunInfoCard label="B" benchmark={benchB} endpoint={epB} />
      </div>

      {/* Quality winner banner */}
      {data.quality_comparison && (
        <QualityWinnerBanner comparison={data.quality_comparison} epA={epA} epB={epB} />
      )}

      <TabBar
        tabs={[
          { id: 'metrics', label: 'Metrics' },
          { id: 'responses', label: 'Responses' },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      {activeTab === 'metrics' && (
        <>
          {/* Key metrics comparison */}
          <div className="bg-surface-800 border border-surface-600 rounded-xl p-4 mb-4">
            <h2 className="font-heading text-sm font-semibold text-gray-300 mb-4">Key Metrics</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-surface-600">
                    <th className="text-left py-2 px-2 text-gray-500 font-semibold w-48">Metric</th>
                    <th className="text-right py-2 px-2 text-accent/70 font-semibold">Run A</th>
                    <th className="text-right py-2 px-2 text-warn/70 font-semibold">Run B</th>
                    <th className="text-right py-2 px-2 text-gray-500 font-semibold">Delta</th>
                  </tr>
                </thead>
                <tbody>
                  <MetricRow label="Total Requests" a={sumA.total_requests} b={sumB.total_requests} format="int" />
                  <MetricRow label="Error Rate %" a={sumA.error_rate_pct} b={sumB.error_rate_pct} format="pct" lowerBetter />
                  <MetricRow label="P50 TTFT (Turn 1)" a={sumA.ttft_t1_p50_ms} b={sumB.ttft_t1_p50_ms} format="ms" lowerBetter
                    tooltip="Median Time to First Token on first turn" />
                  <MetricRow label="P95 TTFT (Turn 1)" a={sumA.ttft_t1_p95_ms} b={sumB.ttft_t1_p95_ms} format="ms" lowerBetter
                    tooltip="95th percentile TTFT on first turn" />
                  <MetricRow label="P50 TGT" a={sumA.tgt_p50_ms} b={sumB.tgt_p50_ms} format="ms" lowerBetter
                    tooltip="Median Total Generation Time" />
                  <MetricRow label="P95 TGT" a={sumA.tgt_p95_ms} b={sumB.tgt_p95_ms} format="ms" lowerBetter
                    tooltip="95th percentile Total Generation Time" />
                  <MetricRow label="P50 tok/s" a={sumA.tps_p50} b={sumB.tps_p50} format="dec" higherBetter
                    tooltip="Median tokens per second" />
                  <MetricRow label="P5 tok/s" a={sumA.tps_p5} b={sumB.tps_p5} format="dec" higherBetter
                    tooltip="5th percentile tokens per second (worst case)" />
                  <MetricRow label="Throughput (req/s)" a={sumA.avg_throughput_rps} b={sumB.avg_throughput_rps} format="dec" higherBetter
                    tooltip="Average requests per second" />
                  <MetricRow label="Total Output Tokens" a={sumA.total_output_tokens} b={sumB.total_output_tokens} format="int" />
                </tbody>
              </table>
            </div>
          </div>

          {/* Quality dimension comparison */}
          {data.quality_comparison && (
            <QualityDimensionComparison comparison={data.quality_comparison} />
          )}

          {/* Quality flag diff */}
          {(sumA.quality_flags || sumB.quality_flags) && (
            <QualityFlagDiff
              flagsA={sumA.quality_flags || {}}
              flagsB={sumB.quality_flags || {}}
              totalA={sumA.successful_requests || 0}
              totalB={sumB.successful_requests || 0}
            />
          )}

          {/* Per-profile comparison */}
          {profilesA && profilesB && (
            <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
              <h2 className="font-heading text-sm font-semibold text-gray-300 mb-4">Per-Profile Breakdown</h2>
              <ProfileComparisonTable profilesA={profilesA} profilesB={profilesB} />
            </div>
          )}
        </>
      )}

      {activeTab === 'responses' && (
        <SideBySideResponses idA={idA} idB={idB} epA={epA} epB={epB} isMatchedSeed={isMatchedSeed} />
      )}
    </div>
  );
}

function RunInfoCard({ label, benchmark, endpoint }) {
  const color = label === 'A' ? 'accent' : 'warn';
  const statusStyles = {
    completed: 'text-green-400',
    aborted: 'text-warn',
    failed: 'text-danger',
  };

  return (
    <div className={`bg-surface-800 border border-${color}/30 rounded-xl p-4`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xs font-bold px-2 py-0.5 rounded bg-${color}/20 text-${color}`}>
          {label}
        </span>
        <span className={`text-[11px] ${statusStyles[benchmark.status] || 'text-gray-400'}`}>
          {benchmark.status}
        </span>
        <span className="text-[10px] text-gray-600 font-mono ml-auto">{benchmark.id.slice(0, 8)}</span>
      </div>
      <div className="text-sm text-gray-200 font-medium mb-1">
        {benchmark.scenario_name || 'Unknown Scenario'}
      </div>
      <div className="flex items-center gap-2 flex-wrap text-[11px] text-gray-500">
        {endpoint.name && <span>{endpoint.name}</span>}
        {endpoint.model_name && <span className="font-mono">{endpoint.model_name}</span>}
        {endpoint.gpu && <span>GPU: {endpoint.gpu}</span>}
        {benchmark.seed != null && <span className="font-mono text-accent/50">seed: {benchmark.seed}</span>}
      </div>
    </div>
  );
}

function MetricRow({ label, a, b, format, lowerBetter, higherBetter, tooltip }) {
  const formatVal = (v) => {
    if (v == null) return '-';
    switch (format) {
      case 'ms': return `${v.toFixed(0)} ms`;
      case 'pct': return `${v.toFixed(1)}%`;
      case 'dec': return v.toFixed(1);
      case 'int': return v.toLocaleString();
      default: return String(v);
    }
  };

  const delta = pct(b, a); // how much B differs from A
  const invertColor = !!higherBetter;

  return (
    <tr className="border-b border-surface-600/50 last:border-b-0">
      <td className="py-2 px-2 text-gray-400">
        <span className="inline-flex items-center gap-1">
          {label}
          {tooltip && <InfoTip text={tooltip} />}
        </span>
      </td>
      <td className="text-right py-2 px-2 text-gray-200">{formatVal(a)}</td>
      <td className="text-right py-2 px-2 text-gray-200">{formatVal(b)}</td>
      <td className="text-right py-2 px-2">
        <DeltaBadge value={delta} invertColor={invertColor} />
      </td>
    </tr>
  );
}

function ProfileComparisonTable({ profilesA, profilesB }) {
  // Build a map of profiles by name
  const mapA = Object.fromEntries(profilesA.map((p) => [p.profile_name, p]));
  const mapB = Object.fromEntries(profilesB.map((p) => [p.profile_name, p]));
  const allNames = [...new Set([...Object.keys(mapA), ...Object.keys(mapB)])];

  if (allNames.length === 0) {
    return <div className="text-gray-500 text-sm text-center py-4">No profile data available</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-surface-600">
            <th className="text-left py-2 px-2 text-gray-500 font-semibold">Profile</th>
            <th className="text-center py-2 px-2 text-gray-500 font-semibold" colSpan="2">Requests</th>
            <th className="text-center py-2 px-2 text-gray-500 font-semibold" colSpan="3">TTFT P50 (ms)</th>
            <th className="text-center py-2 px-2 text-gray-500 font-semibold" colSpan="3">tok/s P50</th>
          </tr>
          <tr className="border-b border-surface-600/50">
            <th />
            <th className="text-right py-1 px-2 text-accent/50 text-[10px]">A</th>
            <th className="text-right py-1 px-2 text-warn/50 text-[10px]">B</th>
            <th className="text-right py-1 px-2 text-accent/50 text-[10px]">A</th>
            <th className="text-right py-1 px-2 text-warn/50 text-[10px]">B</th>
            <th className="text-right py-1 px-2 text-gray-600 text-[10px]">Δ</th>
            <th className="text-right py-1 px-2 text-accent/50 text-[10px]">A</th>
            <th className="text-right py-1 px-2 text-warn/50 text-[10px]">B</th>
            <th className="text-right py-1 px-2 text-gray-600 text-[10px]">Δ</th>
          </tr>
        </thead>
        <tbody>
          {allNames.map((name) => {
            const a = mapA[name] || {};
            const b = mapB[name] || {};
            const ttftDelta = pct(b.ttft_p50, a.ttft_p50);
            const tpsDelta = pct(b.tps_p50, a.tps_p50);

            return (
              <tr key={name} className="border-b border-surface-600/50 last:border-b-0">
                <td className="py-2 px-2 text-gray-200">{name}</td>
                <td className="text-right py-2 px-2 text-gray-300">{a.total_requests ?? '-'}</td>
                <td className="text-right py-2 px-2 text-gray-300">{b.total_requests ?? '-'}</td>
                <td className="text-right py-2 px-2 text-gray-300">{fmt(a.ttft_p50)}</td>
                <td className="text-right py-2 px-2 text-gray-300">{fmt(b.ttft_p50)}</td>
                <td className="text-right py-2 px-2"><DeltaBadge value={ttftDelta} invertColor={false} /></td>
                <td className="text-right py-2 px-2 text-gray-300">{fmt1(a.tps_p50)}</td>
                <td className="text-right py-2 px-2 text-gray-300">{fmt1(b.tps_p50)}</td>
                <td className="text-right py-2 px-2"><DeltaBadge value={tpsDelta} invertColor={true} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// --- Side-by-side response browser ---

const MD_COMPONENTS = {
  h1: ({ children }) => <h1 className="text-sm font-bold text-gray-100 mt-3 mb-1">{children}</h1>,
  h2: ({ children }) => <h2 className="text-sm font-semibold text-gray-100 mt-2.5 mb-1">{children}</h2>,
  h3: ({ children }) => <h3 className="text-xs font-semibold text-gray-200 mt-2 mb-1">{children}</h3>,
  p: ({ children }) => <p className="my-1.5">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-4 my-1.5 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-4 my-1.5 space-y-0.5">{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  code: ({ inline, children }) => inline
    ? <code className="px-1 py-0.5 rounded bg-surface-800 text-accent/80 text-[10px] font-mono">{children}</code>
    : <code>{children}</code>,
  pre: ({ children }) => <pre className="my-2 p-2 rounded bg-surface-800 border border-surface-600 text-[10px] font-mono overflow-x-auto">{children}</pre>,
  strong: ({ children }) => <strong className="font-semibold text-gray-100">{children}</strong>,
  blockquote: ({ children }) => <blockquote className="border-l-2 border-accent/30 pl-3 my-1.5 text-gray-400 italic">{children}</blockquote>,
  table: ({ children }) => <div className="my-2 overflow-x-auto"><table className="min-w-full text-[10px] border border-surface-600 rounded">{children}</table></div>,
  thead: ({ children }) => <thead className="bg-surface-800">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-surface-600/50">{children}</tbody>,
  tr: ({ children }) => <tr className="border-b border-surface-600/50">{children}</tr>,
  th: ({ children }) => <th className="px-2 py-1 text-left font-semibold text-gray-300 border-r border-surface-600/50 last:border-r-0">{children}</th>,
  td: ({ children }) => <td className="px-2 py-1 text-gray-400 border-r border-surface-600/50 last:border-r-0">{children}</td>,
  hr: () => <hr className="my-2 border-surface-600" />,
};

function SideBySideResponses({ idA, idB, epA, epB, isMatchedSeed }) {
  const [sessionIndex, setSessionIndex] = useState(0);
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [totalSessions, setTotalSessions] = useState(0);

  // Get max session count across both benchmarks
  useEffect(() => {
    Promise.all([
      benchmarksApi.sessions(idA, { per_page: 1 }),
      benchmarksApi.sessions(idB, { per_page: 1 }),
    ]).then(([resA, resB]) => {
      setTotalSessions(Math.max(resA.meta.total, resB.meta.total));
    }).catch(() => {});
  }, [idA, idB]);

  // Fetch paired session data
  useEffect(() => {
    setLoading(true);
    benchmarksApi.compareSession(idA, idB, sessionIndex).then((res) => {
      setSessionData(res.data);
    }).catch(() => {
      setSessionData(null);
    }).finally(() => setLoading(false));
  }, [idA, idB, sessionIndex]);

  return (
    <div className="space-y-4">
      {/* Session navigator */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setSessionIndex((i) => Math.max(0, i - 1))}
          disabled={sessionIndex <= 0}
          className="px-3 py-1.5 text-xs rounded-lg bg-surface-700 border border-surface-600 text-gray-300 hover:bg-surface-600 disabled:text-gray-700 disabled:cursor-not-allowed transition-colors"
        >
          ← Prev
        </button>
        <span className="text-sm text-gray-300">
          Session <span className="font-mono text-accent">{sessionIndex + 1}</span> of {totalSessions}
        </span>
        <button
          onClick={() => setSessionIndex((i) => Math.min(totalSessions - 1, i + 1))}
          disabled={sessionIndex >= totalSessions - 1}
          className="px-3 py-1.5 text-xs rounded-lg bg-surface-700 border border-surface-600 text-gray-300 hover:bg-surface-600 disabled:text-gray-700 disabled:cursor-not-allowed transition-colors"
        >
          Next →
        </button>
        {sessionData?.prompt_plan && (
          <span className="ml-2 text-[11px] text-gray-500">
            {sessionData.prompt_plan.prompts?.length || 0} turn(s)
          </span>
        )}
      </div>

      {loading ? (
        <div className="bg-surface-800 border border-surface-600 rounded-xl p-12 flex items-center justify-center gap-2 text-gray-500 text-sm">
          <Spinner size="sm" /> Loading session...
        </div>
      ) : !sessionData ? (
        <div className="bg-surface-800 border border-surface-600 rounded-xl p-12 text-center text-gray-500 text-sm">
          No data available for this session.
        </div>
      ) : (
        <SessionComparison
          data={sessionData}
          labelA={epA.name || 'Run A'}
          labelB={epB.name || 'Run B'}
          isMatchedSeed={isMatchedSeed}
        />
      )}
    </div>
  );
}

function SessionComparison({ data, labelA, labelB, isMatchedSeed }) {
  const { a: reqsA, b: reqsB, prompt_plan } = data;
  const maxTurns = Math.max(reqsA.length, reqsB.length);

  if (maxTurns === 0) {
    return <div className="text-gray-500 text-sm text-center py-8">No turns in this session.</div>;
  }

  return (
    <div className="space-y-4">
      {Array.from({ length: maxTurns }, (_, turn) => {
        const rA = reqsA[turn];
        const rB = reqsB[turn];

        if (isMatchedSeed) {
          // Matched seeds: shared user prompt spanning full width
          const userPrompt = prompt_plan?.prompts?.[turn] || _extractUserMessage(rA) || _extractUserMessage(rB);
          return (
            <div key={turn} className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                  Turn {turn + 1}
                </span>
                <div className="flex-1 h-px bg-surface-600" />
              </div>
              {userPrompt && (
                <div className="bg-surface-700 border border-surface-600 rounded-lg px-4 py-2">
                  <div className="text-[9px] uppercase tracking-wider text-gray-600 mb-1">User</div>
                  <div className="text-xs text-gray-300 whitespace-pre-wrap break-words leading-relaxed">
                    {userPrompt}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <ResponsePanel label={labelA} color="accent" request={rA} />
                <ResponsePanel label={labelB} color="warn" request={rB} />
              </div>
            </div>
          );
        }

        // Non-matched: each side shows its own prompt + response
        const promptA = _extractUserMessage(rA);
        const promptB = _extractUserMessage(rB);
        return (
          <div key={turn} className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                Turn {turn + 1}
              </span>
              <div className="flex-1 h-px bg-surface-600" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <ResponsePanel label={labelA} color="accent" request={rA} userPrompt={promptA} />
              <ResponsePanel label={labelB} color="warn" request={rB} userPrompt={promptB} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ResponsePanel({ label, color, request, userPrompt }) {
  const r = request;
  const borderColor = color === 'accent' ? 'border-accent/20' : 'border-warn/20';
  const bgColor = color === 'accent' ? 'bg-accent/5' : 'bg-warn/5';
  const labelColor = color === 'accent' ? 'text-accent/50' : 'text-warn/50';

  if (!r) {
    return (
      <div className={`${bgColor} border ${borderColor} rounded-lg px-4 py-3`}>
        <div className={`text-[9px] uppercase tracking-wider ${labelColor} mb-1`}>{label}</div>
        <div className="text-xs text-gray-600 italic">No data for this session</div>
      </div>
    );
  }

  const hasError = r.error_type != null;

  return (
    <div className={`${bgColor} border ${borderColor} rounded-lg px-4 py-3`}>
      {/* User prompt (shown in non-matched mode) */}
      {userPrompt && (
        <div className="bg-surface-700/50 border border-surface-600 rounded px-3 py-2 mb-3">
          <div className="text-[9px] uppercase tracking-wider text-gray-600 mb-1">User</div>
          <div className="text-xs text-gray-300 whitespace-pre-wrap break-words leading-relaxed">
            {userPrompt.length > 800 ? userPrompt.slice(0, 800) + '...' : userPrompt}
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 mb-2">
        <span className={`text-[9px] uppercase tracking-wider ${labelColor}`}>{label}</span>
        <div className="flex items-center gap-2 ml-auto text-[10px] text-gray-500">
          <span>TTFT {r.ttft_ms != null ? `${r.ttft_ms.toFixed(0)}ms` : '-'}</span>
          <span className="text-gray-700">|</span>
          <span>{r.tokens_per_second != null ? `${r.tokens_per_second.toFixed(1)} tok/s` : '-'}</span>
          <span className="text-gray-700">|</span>
          <span>{r.output_tokens ?? 0} tok</span>
        </div>
      </div>

      {r.quality_flags && r.quality_flags.length > 0 && (
        <div className="flex items-center gap-1 mb-2">
          {r.quality_flags.map((f) => <QualityFlagPill key={f} flag={f} />)}
        </div>
      )}

      {hasError ? (
        <div className="text-xs text-danger/80 whitespace-pre-wrap break-words">
          {r.error_detail || r.error_type || 'Error'}
        </div>
      ) : r.response_text ? (
        <div className="text-xs text-gray-200 break-words leading-relaxed">
          <Markdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
            {r.response_text.length > 3000
              ? r.response_text.slice(0, 3000) + '\n\n...'
              : r.response_text}
          </Markdown>
        </div>
      ) : (
        <div className="text-xs text-gray-600 italic">Empty response</div>
      )}
    </div>
  );
}

// --- Quality comparison components ---

const QUALITY_DIMENSIONS = ['completeness', 'compliance', 'coherence', 'safety'];
const QUALITY_LABELS = {
  completeness: 'Completeness',
  compliance: 'Compliance',
  coherence: 'Coherence',
  safety: 'Safety',
  overall: 'Overall',
};

function QualityWinnerBanner({ comparison, epA, epB }) {
  const { winner, dimensions } = comparison;
  const overall = dimensions.overall;
  const scoreA = Math.round((overall?.a ?? 0) * 100);
  const scoreB = Math.round((overall?.b ?? 0) * 100);

  if (winner === 'tie') {
    return (
      <div className="bg-surface-800 border border-surface-600 rounded-xl px-4 py-3 mb-4 flex items-center justify-center gap-3">
        <span className="text-xs text-gray-400">Quality:</span>
        <span className="text-sm font-medium text-gray-300">Tie</span>
        <span className="text-xs font-mono text-gray-500">{scoreA}% vs {scoreB}%</span>
      </div>
    );
  }

  const winnerLabel = winner === 'a' ? (epA.name || 'Run A') : (epB.name || 'Run B');
  const winnerColor = winner === 'a' ? 'accent' : 'warn';
  const winnerScore = winner === 'a' ? scoreA : scoreB;
  const loserScore = winner === 'a' ? scoreB : scoreA;

  return (
    <div className={`bg-surface-800 border border-${winnerColor}/30 rounded-xl px-4 py-3 mb-4 flex items-center gap-3`}>
      <span className="text-xs text-gray-400">Quality Winner:</span>
      <span className={`text-sm font-semibold px-2 py-0.5 rounded bg-${winnerColor}/20 text-${winnerColor}`}>
        {winner === 'a' ? 'A' : 'B'}
      </span>
      <span className="text-sm font-medium text-gray-200">{winnerLabel}</span>
      <span className="text-xs font-mono text-gray-500 ml-auto">
        {winnerScore}% vs {loserScore}%
      </span>
    </div>
  );
}

function QualityDimensionComparison({ comparison }) {
  const { dimensions } = comparison;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4 mb-4">
      <h2 className="font-heading text-sm font-semibold text-gray-300 mb-4">
        Quality Dimensions
        <span className="ml-2">
          <InfoTip text="Per-dimension quality scores comparing both runs. Scores are 0-100% based on heuristic checks of LLM responses." />
        </span>
      </h2>
      <div className="space-y-3">
        {[...QUALITY_DIMENSIONS, 'overall'].map((dim) => {
          const d = dimensions[dim];
          if (!d) return null;
          const aVal = Math.round((d.a ?? 0) * 100);
          const bVal = Math.round((d.b ?? 0) * 100);
          const isOverall = dim === 'overall';

          return (
            <div key={dim} className={`${isOverall ? 'pt-3 border-t border-surface-600' : ''}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`w-28 text-[11px] ${isOverall ? 'font-semibold text-gray-300' : 'text-gray-400'}`}>
                  {QUALITY_LABELS[dim]}
                </span>
                <div className="flex-1 flex items-center gap-1">
                  {/* Bar A */}
                  <div className="flex-1 h-3 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent transition-all duration-500"
                      style={{ width: `${aVal}%`, opacity: aVal > 0 ? 0.8 : 0 }}
                    />
                  </div>
                  {/* Bar B */}
                  <div className="flex-1 h-3 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-warn transition-all duration-500"
                      style={{ width: `${bVal}%`, opacity: bVal > 0 ? 0.8 : 0 }}
                    />
                  </div>
                </div>
                <span className="w-12 text-right text-[11px] font-mono text-accent/70">{aVal}%</span>
                <span className="w-12 text-right text-[11px] font-mono text-warn/70">{bVal}%</span>
                <span className="w-14 text-right">
                  {d.delta !== 0 && (
                    <span className={`text-[10px] font-mono ${d.delta > 0 ? 'text-green-400' : d.delta < 0 ? 'text-danger' : 'text-gray-500'}`}>
                      {d.delta > 0 ? '+' : ''}{Math.round(d.delta * 100)}
                    </span>
                  )}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 mt-3 pt-2 border-t border-surface-600/50">
        <span className="text-[10px] text-accent/50 flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-accent/80 inline-block" /> Run A
        </span>
        <span className="text-[10px] text-warn/50 flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-warn/80 inline-block" /> Run B
        </span>
        <span className="text-[10px] text-gray-600 ml-auto">Delta: A relative to B</span>
      </div>
    </div>
  );
}

function QualityFlagDiff({ flagsA, flagsB, totalA, totalB }) {
  const allFlags = [...new Set([...Object.keys(flagsA), ...Object.keys(flagsB)])];
  if (allFlags.length === 0) return null;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4 mb-4">
      <h2 className="font-heading text-sm font-semibold text-gray-300 mb-4">Quality Flag Comparison</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-surface-600">
              <th className="text-left py-2 px-2 text-gray-500 font-semibold">Flag</th>
              <th className="text-right py-2 px-2 text-accent/70 font-semibold">A Count</th>
              <th className="text-right py-2 px-2 text-accent/70 font-semibold">A %</th>
              <th className="text-right py-2 px-2 text-warn/70 font-semibold">B Count</th>
              <th className="text-right py-2 px-2 text-warn/70 font-semibold">B %</th>
              <th className="text-right py-2 px-2 text-gray-500 font-semibold">Change</th>
            </tr>
          </thead>
          <tbody>
            {allFlags.sort().map((flag) => {
              const countA = flagsA[flag] || 0;
              const countB = flagsB[flag] || 0;
              const pctA = totalA > 0 ? (countA / totalA * 100) : 0;
              const pctB = totalB > 0 ? (countB / totalB * 100) : 0;
              const diff = countA - countB;

              return (
                <tr key={flag} className="border-b border-surface-600/50 last:border-b-0">
                  <td className="py-2 px-2"><QualityFlagPill flag={flag} /></td>
                  <td className="text-right py-2 px-2 text-gray-300">{countA}</td>
                  <td className="text-right py-2 px-2 text-gray-500">{pctA.toFixed(1)}%</td>
                  <td className="text-right py-2 px-2 text-gray-300">{countB}</td>
                  <td className="text-right py-2 px-2 text-gray-500">{pctB.toFixed(1)}%</td>
                  <td className="text-right py-2 px-2">
                    {diff !== 0 && (
                      <span className={`text-[10px] ${diff < 0 ? 'text-green-400' : 'text-danger'}`}>
                        {diff > 0 ? '+' : ''}{diff}
                      </span>
                    )}
                    {diff === 0 && <span className="text-gray-600">=</span>}
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

function _extractUserMessage(request) {
  if (!request?.request_body?.messages) return null;
  const msgs = request.request_body.messages;
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'user') {
      const content = msgs[i].content;
      return typeof content === 'string' ? content : JSON.stringify(content);
    }
  }
  return null;
}
