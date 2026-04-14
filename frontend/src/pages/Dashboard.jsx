import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardApi } from '../api/client';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import InfoTip from '../components/InfoTip';

function HealthDot({ status }) {
  const color = status === 'healthy' ? 'bg-green-400' : status === 'error' ? 'bg-danger' : 'bg-gray-500';
  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${color}`} />
      <span className={`text-xs ${status === 'healthy' ? 'text-green-400' : status === 'error' ? 'text-danger' : 'text-gray-500'}`}>
        {status}
      </span>
    </div>
  );
}

function formatTokens(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDuration(seconds) {
  if (seconds == null) return '-';
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  if (seconds >= 60) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  return `${Math.round(seconds)}s`;
}

function formatTime(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function qualityColor(score) {
  if (score >= 0.9) return 'text-green-400';
  if (score >= 0.7) return 'text-accent';
  if (score >= 0.5) return 'text-warn';
  return 'text-danger';
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [health, setHealth] = useState({ api: 'loading', db: 'loading', mock: 'loading' });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/health')
      .then((r) => r.json())
      .then((d) => {
        const c = d.data.components;
        setHealth({
          api: d.data.status === 'healthy' ? 'healthy' : 'error',
          db: c.database,
          mock: c.mock_llm === 'healthy' ? 'healthy' : 'error',
        });
      })
      .catch(() => setHealth({ api: 'error', db: 'error', mock: 'error' }));

    dashboardApi.get()
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const isEmpty = !data || data.fleet.total_benchmarks === 0;

  return (
    <div>
      <h1 className="font-heading text-2xl font-bold mb-6">Dashboard</h1>

      {/* Health status row */}
      <div className="flex items-center gap-6 mb-4 px-4 py-2.5 bg-surface-800 border border-surface-600 rounded-xl">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-gray-600">API</span>
          <HealthDot status={health.api} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-gray-600">Database</span>
          <HealthDot status={health.db} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-gray-600">Mock LLM</span>
          <HealthDot status={health.mock} />
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      )}

      {!loading && isEmpty && (
        <div className="bg-surface-800 border border-surface-600 rounded-xl p-8 text-center">
          <p className="text-gray-400 font-heading text-lg mb-2">Ready to benchmark</p>
          <p className="text-gray-600 text-sm mb-4">
            Create a scenario and endpoint, then run your first benchmark to populate this dashboard.
          </p>
          <button
            onClick={() => navigate('/benchmarks')}
            className="px-5 py-2 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors"
          >
            Go to Benchmarks
          </button>
        </div>
      )}

      {!loading && !isEmpty && (
        <>
          {/* Fleet overview metric cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <MetricCard
              label="Benchmarks"
              value={data.fleet.total_benchmarks}
              tooltip="Total completed, aborted, and failed benchmark runs"
            />
            <MetricCard
              label="Total Requests"
              value={formatTokens(data.fleet.total_requests)}
              tooltip="Total LLM requests across all benchmarks"
            />
            <MetricCard
              label="Tokens Generated"
              value={formatTokens(data.fleet.total_output_tokens)}
              subtitle={`${formatTokens(data.fleet.total_input_tokens)} input`}
              tooltip="Total output tokens generated across all benchmarks"
            />
            <MetricCard
              label="Avg Quality"
              value={data.fleet.avg_quality_overall != null ? `${Math.round(data.fleet.avg_quality_overall * 100)}%` : '-'}
              color={data.fleet.avg_quality_overall != null && data.fleet.avg_quality_overall < 0.7 ? 'danger' : undefined}
              tooltip="Average quality score across all benchmarks (weighted: completeness, compliance, coherence, safety)"
            />
          </div>

          {/* Endpoint performance table */}
          {data.endpoints.length > 0 && (
            <div className="bg-surface-800 border border-surface-600 rounded-xl mb-4 overflow-hidden">
              <div className="px-4 py-3 border-b border-surface-600">
                <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold inline-flex items-center gap-1.5">
                  Endpoint Performance
                  <InfoTip text="Aggregated metrics across all benchmark runs per endpoint. TTFT and TPS are averages of per-run medians." />
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-gray-600 border-b border-surface-600">
                      <th className="text-left py-2.5 px-4">Endpoint</th>
                      <th className="text-left py-2.5 px-3">Model</th>
                      <th className="text-center py-2.5 px-3">Runs</th>
                      <th className="text-right py-2.5 px-3">
                        <span className="inline-flex items-center gap-1">
                          TTFT p50
                          <InfoTip text="Average first-turn Time to First Token (median) across runs" />
                        </span>
                      </th>
                      <th className="text-right py-2.5 px-3">
                        <span className="inline-flex items-center gap-1">
                          tok/s
                          <InfoTip text="Average token generation speed (median) across runs" />
                        </span>
                      </th>
                      <th className="text-right py-2.5 px-3">Quality</th>
                      <th className="text-right py-2.5 px-3">Tokens</th>
                      <th className="text-right py-2.5 px-4">Last Run</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.endpoints.map((ep) => (
                      <tr key={ep.endpoint_id} className="border-t border-surface-600/50 hover:bg-surface-700/50 transition-colors">
                        <td className="py-2.5 px-4">
                          <div className="text-gray-200 font-medium">{ep.name}</div>
                          {ep.gpu && <div className="text-[10px] text-gray-600">{ep.gpu}{ep.inference_engine ? ` / ${ep.inference_engine}` : ''}</div>}
                        </td>
                        <td className="py-2.5 px-3 text-gray-400 font-mono">{ep.model_name || '-'}</td>
                        <td className="py-2.5 px-3 text-center text-gray-400 tabular-nums">{ep.run_count}</td>
                        <td className="py-2.5 px-3 text-right font-mono text-gray-300 tabular-nums">
                          {ep.avg_ttft_p50 != null ? `${Math.round(ep.avg_ttft_p50)} ms` : '-'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-gray-300 tabular-nums">
                          {ep.avg_tps_p50 != null ? ep.avg_tps_p50.toFixed(1) : '-'}
                        </td>
                        <td className={`py-2.5 px-3 text-right font-mono tabular-nums ${ep.avg_quality_overall != null ? qualityColor(ep.avg_quality_overall) : 'text-gray-600'}`}>
                          {ep.avg_quality_overall != null ? `${Math.round(ep.avg_quality_overall * 100)}%` : '-'}
                        </td>
                        <td className="py-2.5 px-3 text-right text-gray-500 tabular-nums">
                          <span className="text-gray-400">{formatTokens(ep.total_output_tokens)}</span>
                          <span className="text-gray-600 text-[10px] ml-1">out</span>
                        </td>
                        <td className="py-2.5 px-4 text-right text-gray-500">{formatTime(ep.last_run_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Recent runs */}
          {data.recent_runs.length > 0 && (
            <div className="bg-surface-800 border border-surface-600 rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-surface-600">
                <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Recent Runs</h3>
              </div>
              <div>
                {data.recent_runs.map((run) => (
                  <div
                    key={run.id}
                    onClick={() => navigate(`/benchmarks/${run.id}`)}
                    className="flex items-center gap-3 px-4 py-3 border-b border-surface-600/50 last:border-b-0 hover:bg-surface-700/50 cursor-pointer transition-colors"
                  >
                    <StatusBadge status={run.status} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-gray-200 font-medium truncate block">{run.scenario_name || 'Unknown'}</span>
                      <span className="text-[10px] text-gray-600">
                        {run.endpoint_name}{run.model_name ? ` / ${run.model_name}` : ''}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500 tabular-nums">
                      <span>{run.total_requests} req</span>
                      <span>{formatDuration(run.duration_seconds)}</span>
                      <span className="text-gray-600">{formatTime(run.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
