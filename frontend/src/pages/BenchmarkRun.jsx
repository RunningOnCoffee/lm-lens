import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { benchmarksApi } from '../api/client';
import useWebSocket from '../hooks/useWebSocket';
import TabBar from '../components/TabBar';
import AnalysisTab from '../components/AnalysisTab';
import InfoTip from '../components/InfoTip';
import MetricCard from '../components/MetricCard';
import LatencyTimeline from '../components/charts/LatencyTimeline';
import ThroughputChart from '../components/charts/ThroughputChart';
import ErrorChart from '../components/charts/ErrorChart';
import ProfileBreakdown from '../components/charts/ProfileBreakdown';
import QualityLoadChart from '../components/charts/QualityLoadChart';
import RequestLog from '../components/RequestLog';
import ResponseBrowser from '../components/ResponseBrowser';
import QualityFlagPill from '../components/QualityFlagPill';
import QualityScorecard from '../components/QualityScorecard';

export default function BenchmarkRun() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [benchmark, setBenchmark] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isActive = benchmark?.status === 'running' || benchmark?.status === 'pending';
  const { snapshots: liveSnapshots, connected } = useWebSocket(id, { enabled: isActive });
  const [historicalSnapshots, setHistoricalSnapshots] = useState(null);
  const [historicalRequests, setHistoricalRequests] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [aborting, setAborting] = useState(false);

  // Use live snapshots during run, historical for completed
  const snapshots = isActive ? liveSnapshots : (historicalSnapshots || []);
  const latest = snapshots[snapshots.length - 1] || null;

  // Load benchmark details
  useEffect(() => {
    (async () => {
      try {
        const res = await benchmarksApi.get(id);
        setBenchmark(res.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  // Load historical snapshots + requests for completed benchmarks
  useEffect(() => {
    if (!benchmark || isActive) return;
    (async () => {
      try {
        const res = await benchmarksApi.snapshots(id);
        setHistoricalSnapshots(res.data);
      } catch {
        setHistoricalSnapshots([]);
      }
      try {
        const res = await benchmarksApi.requests(id, { per_page: 200 });
        setHistoricalRequests(res.data);
      } catch {
        setHistoricalRequests([]);
      }
    })();
  }, [id, benchmark, isActive]);

  // Poll status while active
  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(async () => {
      try {
        const res = await benchmarksApi.get(id);
        setBenchmark(res.data);
        if (res.data.status !== 'running' && res.data.status !== 'pending') {
          const snapRes = await benchmarksApi.snapshots(id);
          setHistoricalSnapshots(snapRes.data);
        }
      } catch {
        // ignore poll errors
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [id, isActive]);

  const handleAbort = async () => {
    setAborting(true);
    try {
      await benchmarksApi.abort(id);
      const res = await benchmarksApi.get(id);
      setBenchmark(res.data);
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading benchmark...</p>
      </div>
    );
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

  const summary = benchmark.results_summary;
  const hasLiveData = isActive && latest != null;
  const hasSummary = summary != null && !summary.error;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => navigate('/benchmarks')} className="text-xs text-gray-500 hover:text-gray-300 mb-1 block">
            &larr; Back to Benchmarks
          </button>
          <h1 className="font-heading text-2xl font-bold">
            {benchmark.scenario_name || 'Benchmark'}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            <StatusBadge status={benchmark.status} />
            {isActive && connected && (
              <span className="flex items-center gap-1 text-[11px] text-green-400">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                Live
              </span>
            )}
            <span className="text-xs text-gray-600 font-mono">{id.slice(0, 8)}</span>
            {benchmark.seed != null && (
              <span className="text-[11px] text-accent/50 font-mono">seed: {benchmark.seed}</span>
            )}
          </div>
          {benchmark.endpoint_snapshot && benchmark.endpoint_snapshot.name && (
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <span className="px-2 py-0.5 text-[11px] rounded bg-surface-700 text-gray-300">
                {benchmark.endpoint_snapshot.name}
              </span>
              {benchmark.endpoint_snapshot.model_name && (
                <span className="px-2 py-0.5 text-[11px] rounded bg-surface-700 text-gray-400 font-mono">
                  {benchmark.endpoint_snapshot.model_name}
                </span>
              )}
              {benchmark.endpoint_snapshot.gpu && (
                <span className="px-2 py-0.5 text-[11px] rounded bg-surface-700 text-gray-500">
                  GPU: {benchmark.endpoint_snapshot.gpu}
                </span>
              )}
              {benchmark.endpoint_snapshot.inference_engine && (
                <span className="px-2 py-0.5 text-[11px] rounded bg-surface-700 text-gray-500">
                  {benchmark.endpoint_snapshot.inference_engine}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4">
          {isActive && hasLiveData && latest.duration_seconds > 0 && (
            <CountdownTimer
              elapsedSeconds={latest.elapsed_seconds}
              durationSeconds={latest.duration_seconds}
            />
          )}
          {isActive && (
            <button
              onClick={handleAbort}
              disabled={aborting}
              className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                aborting
                  ? 'bg-warn/5 text-warn/50 border-warn/20 cursor-not-allowed'
                  : 'bg-warn/10 text-warn hover:bg-warn/20 border-warn/30'
              }`}
            >
              {aborting ? 'Aborting…' : 'Abort'}
            </button>
          )}
          {!isActive && (
            <ExportDropdown benchmarkId={id} />
          )}
        </div>
      </div>

      {/* Active runs: show everything inline (no tabs) */}
      {isActive ? (
        <>
          {hasLiveData ? (
            <LiveMetrics snapshot={latest} />
          ) : (
            <div className="p-8 bg-surface-800 border border-surface-600 rounded-xl text-center text-gray-500 text-sm mb-6">
              Waiting for data...
            </div>
          )}

          {snapshots.length > 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <LatencyTimeline snapshots={snapshots} breakingPoint={summary?.breaking_point} />
                <ThroughputChart snapshots={snapshots} />
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ErrorChart snapshots={snapshots} />
                <ProfileBreakdown snapshots={snapshots} />
              </div>
              <QualityLoadChart snapshots={snapshots} />
            </div>
          )}
          {snapshots.length <= 1 && (
            <div className="p-8 bg-surface-800 border border-surface-600 rounded-xl text-center text-gray-600 text-sm">
              Collecting data points for charts...
            </div>
          )}

          <RequestLog snapshots={snapshots} historicalRequests={historicalRequests} />
        </>
      ) : (
        <>
          {/* Completed/aborted/failed: show tabs */}
          <TabBar
            tabs={[
              { id: 'overview', label: 'Overview' },
              { id: 'analysis', label: 'Analysis' },
              { id: 'responses', label: 'Responses' },
            ]}
            activeTab={activeTab}
            onChange={setActiveTab}
          />

          {activeTab === 'overview' && (
            <>
              {hasSummary ? (
                <SummaryMetrics summary={summary} />
              ) : (
                <div className="p-8 bg-surface-800 border border-surface-600 rounded-xl text-center text-gray-500 text-sm mb-6">
                  No metrics available for this benchmark.
                </div>
              )}

              <QualityScorecard benchmarkId={id} />

              {snapshots.length > 1 && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <LatencyTimeline snapshots={snapshots} breakingPoint={summary?.breaking_point} />
                    <ThroughputChart snapshots={snapshots} />
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <ErrorChart snapshots={snapshots} />
                    <ProfileBreakdown snapshots={snapshots} />
                  </div>
                  <QualityLoadChart snapshots={snapshots} />
                </div>
              )}
              {snapshots.length <= 1 && !hasSummary && (
                <div className="p-8 bg-surface-800 border border-surface-600 rounded-xl text-center text-gray-600 text-sm">
                  Not enough data points to render charts.
                </div>
              )}

              <RequestLog snapshots={snapshots} historicalRequests={historicalRequests} />
            </>
          )}

          {activeTab === 'analysis' && (
            <AnalysisTab benchmarkId={id} />
          )}

          {activeTab === 'responses' && (
            <ResponseBrowser benchmarkId={id} />
          )}
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    pending: 'bg-gray-500/20 text-gray-400',
    running: 'bg-accent/20 text-accent',
    completed: 'bg-green-500/20 text-green-400',
    aborted: 'bg-warn/20 text-warn',
    failed: 'bg-danger/20 text-danger',
  };
  return (
    <span className={`px-2 py-0.5 text-[11px] rounded-full font-medium ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}

function CountdownTimer({ elapsedSeconds, durationSeconds }) {
  const overrun = elapsedSeconds > durationSeconds;
  const remaining = Math.max(0, durationSeconds - elapsedSeconds);
  const pct = Math.min(100, (elapsedSeconds / durationSeconds) * 100);

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  if (overrun) {
    return (
      <div className="text-right">
        <div className="text-sm font-mono font-semibold text-warn">
          Finishing...
        </div>
        <div className="text-[10px] text-gray-500 uppercase tracking-wider">
          completing remaining requests
        </div>
        <div className="w-32 h-1 bg-surface-700 rounded-full mt-1 overflow-hidden">
          <div className="h-full bg-warn rounded-full w-full animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="text-right">
      <div className="text-lg font-mono font-semibold text-gray-100">
        {formatTime(remaining)}
      </div>
      <div className="text-[10px] text-gray-500 uppercase tracking-wider">remaining</div>
      <div className="w-32 h-1 bg-surface-700 rounded-full mt-1 overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-1000"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function LiveMetrics({ snapshot }) {
  const s = snapshot;
  const TPS_SLOW_THRESHOLD = 10;

  return (
    <div className="mb-6">
      {/* Row 1: Status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Active Users" value={s.active_users} />
        <MetricCard label="Completed" value={s.completed_requests} />
        <MetricCard
          label="Failed"
          value={s.failed_requests}
          color={s.failed_requests > 0 ? 'danger' : undefined}
        />
        <MetricCard
          label="Error Rate"
          value={
            (s.completed_requests + s.failed_requests) > 0
              ? `${((s.failed_requests / (s.completed_requests + s.failed_requests)) * 100).toFixed(1)}%`
              : '0%'
          }
          color={s.failed_requests > 0 ? 'danger' : undefined}
        />
      </div>

      {/* Row 2: Performance (rolling 30s window) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="P50 TTFT (Turn 1)"
          tooltip="Time to First Token — how long until the model starts responding. P50 = median (half of requests are faster). Measured on the first turn only, before conversation context grows."
          value={s.rolling_p50_ttft_t1_ms != null ? `${s.rolling_p50_ttft_t1_ms.toFixed(0)} ms` : '-'}
          subtitle="last 30s"
        />
        <MetricCard
          label="P95 TTFT (Turn 1)"
          tooltip="Time to First Token at the 95th percentile — only 5% of requests take longer than this. High P95 indicates occasional slowdowns even if the median is fast."
          value={s.rolling_p95_ttft_t1_ms != null ? `${s.rolling_p95_ttft_t1_ms.toFixed(0)} ms` : '-'}
          subtitle="last 30s"
        />
        <MetricCard
          label="Median tok/s"
          tooltip="Tokens per second — how fast the model generates output text. Higher is better. This is the median (P50) generation speed across recent requests."
          value={s.rolling_avg_tps != null ? s.rolling_avg_tps.toFixed(1) : '-'}
          subtitle="last 30s"
        />
        <MetricCard
          label="Slow tok/s (P5)"
          tooltip="The slowest 5% of requests by generation speed. If this drops significantly below the median, some requests are experiencing severe slowdowns."
          value={s.rolling_p5_tps != null ? s.rolling_p5_tps.toFixed(1) : '-'}
          subtitle="last 30s"
          color={s.rolling_p5_tps != null && s.rolling_p5_tps < TPS_SLOW_THRESHOLD ? 'danger' : 'ok'}
        />
      </div>
    </div>
  );
}

function SummaryMetrics({ summary }) {
  const hasMultiTurn = summary.ttft_multi_p50_ms != null;
  const fmt = (v) => v != null ? v.toFixed(0) : '-';
  const fmt1 = (v) => v != null ? v.toFixed(1) : '-';

  return (
    <div className="mb-6 space-y-3">
      {/* Row 1: Status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Total Requests" value={summary.total_requests} />
        <MetricCard label="Successful" value={summary.successful_requests} />
        <MetricCard
          label="Failed"
          value={summary.failed_requests}
          color={summary.failed_requests > 0 ? 'danger' : undefined}
        />
        <MetricCard
          label="Error Rate"
          value={`${summary.error_rate_pct.toFixed(1)}%`}
          color={summary.error_rate_pct > 0 ? 'danger' : undefined}
        />
      </div>

      {/* Row 2: First-turn performance (primary comparison metric) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="P50 TTFT (Turn 1)"
          tooltip="Time to First Token — how long until the model starts responding. P50 = median (half of requests are faster). Measured on the first turn only, before conversation context grows."
          value={`${fmt(summary.ttft_t1_p50_ms)} ms`}
          subtitle="first turn"
        />
        <MetricCard
          label="P95 TTFT (Turn 1)"
          tooltip="Time to First Token at the 95th percentile — only 5% of requests take longer than this. High P95 indicates occasional slowdowns even if the median is fast."
          value={`${fmt(summary.ttft_t1_p95_ms)} ms`}
          subtitle="first turn"
        />
        <MetricCard
          label="P50 tok/s"
          tooltip="Tokens per second — how fast the model generates output text. Higher is better. This is the median generation speed across all requests."
          value={fmt1(summary.tps_p50)}
          subtitle="generation speed"
        />
        <MetricCard
          label="Slow tok/s (P5)"
          tooltip="The slowest 5% of requests by generation speed. If this drops significantly below the median, some requests are experiencing severe slowdowns."
          value={fmt1(summary.tps_p5)}
          subtitle="worst 5%"
          color={summary.tps_p5 != null && summary.tps_p5 < 10 ? 'danger' : 'ok'}
        />
      </div>

      {/* Row 3: Multi-turn + totals (only if multi-turn data exists) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {hasMultiTurn ? (
          <>
            <MetricCard
              label="P50 TTFT (Multi-Turn)"
              tooltip="Time to First Token for follow-up turns in a conversation. These requests include prior conversation context, so they're typically slower than first-turn TTFT."
              value={`${fmt(summary.ttft_multi_p50_ms)} ms`}
              subtitle="context-heavy"
            />
            <MetricCard
              label="P95 TTFT (Multi-Turn)"
              tooltip="95th percentile Time to First Token for follow-up turns. Shows how the model handles growing conversation context under load."
              value={`${fmt(summary.ttft_multi_p95_ms)} ms`}
              subtitle="context-heavy"
            />
          </>
        ) : (
          <>
            <MetricCard
              label="P50 TGT"
              tooltip="Total Generation Time — the full time from sending the request to receiving the last token. Includes TTFT + all token generation time."
              value={`${fmt(summary.tgt_p50_ms)} ms`}
              subtitle="total generation"
            />
            <MetricCard
              label="P95 TGT"
              tooltip="Total Generation Time at the 95th percentile. Shows the worst-case total response time for most requests."
              value={`${fmt(summary.tgt_p95_ms)} ms`}
              subtitle="total generation"
            />
          </>
        )}
        <MetricCard
          label="Output Tokens"
          tooltip="Total number of tokens generated across all requests in this benchmark run."
          value={(summary.total_output_tokens || 0).toLocaleString()}
        />
        <MetricCard
          label="Throughput"
          tooltip="Average successful requests completed per second over the entire run duration."
          value={summary.avg_throughput_rps != null ? `${summary.avg_throughput_rps} req/s` : '-'}
          subtitle="avg over run"
        />
      </div>

      {/* Quality flags (only if any exist) */}
      {summary.quality_flags && Object.values(summary.quality_flags).some((v) => v > 0) && (
        <div className="bg-surface-800 border border-surface-600 rounded-xl p-3">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-[10px] uppercase tracking-wider text-gray-600 mr-1">
              Quality Flags
            </span>
            <InfoTip text="Quality flags are automatically detected issues in LLM responses. Truncated = hit max_tokens limit. Empty = no output generated. Refusal = model declined to answer. Repeated = suspiciously repetitive output." />
            {Object.entries(summary.quality_flags)
              .filter(([, count]) => count > 0)
              .map(([flag, count]) => (
                <span key={flag} className="inline-flex items-center gap-1.5">
                  <QualityFlagPill flag={flag} />
                  <span className="text-xs font-mono text-gray-400">{count}</span>
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}


function ExportDropdown({ benchmarkId }) {
  const [open, setOpen] = useState(false);
  const [exporting, setExporting] = useState(null);

  const handleExport = async (format) => {
    setExporting(format);
    try {
      if (format === 'csv') {
        await benchmarksApi.exportCSV(benchmarkId);
      } else {
        await benchmarksApi.exportJSON(benchmarkId);
      }
    } catch {
      // silently fail — file download
    } finally {
      setExporting(null);
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="px-4 py-2 text-sm rounded-lg bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 hover:text-accent-bright transition-colors font-medium"
      >
        Export ▾
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 w-36 bg-surface-700 border border-surface-600 rounded-lg shadow-lg z-50 overflow-hidden">
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting != null}
              className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-surface-600 transition-colors disabled:text-gray-600"
            >
              {exporting === 'csv' ? 'Exporting…' : 'Download CSV'}
            </button>
            <button
              onClick={() => handleExport('json')}
              disabled={exporting != null}
              className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-surface-600 transition-colors disabled:text-gray-600 border-t border-surface-600"
            >
              {exporting === 'json' ? 'Exporting…' : 'Download JSON'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
