import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useBenchmarkStore from '../stores/benchmarkStore';
import useScenarioStore from '../stores/scenarioStore';
import useEndpointStore from '../stores/endpointStore';

const STATUS_STYLES = {
  pending:   'bg-gray-500/20 text-gray-400',
  running:   'bg-accent/20 text-accent',
  completed: 'bg-green-500/20 text-green-400',
  aborted:   'bg-warn/20 text-warn',
  failed:    'bg-danger/20 text-danger',
};

function StatusBadge({ status }) {
  return (
    <span className={`px-2 py-0.5 text-[11px] rounded-full font-medium ${STATUS_STYLES[status] || STATUS_STYLES.pending}`}>
      {status}
    </span>
  );
}

export default function Benchmarks() {
  const { benchmarks, loading, error, fetchBenchmarks, startBenchmark, deleteBenchmark, abortBenchmark } = useBenchmarkStore();
  const { scenarios, fetchScenarios } = useScenarioStore();
  const { endpoints, fetchEndpoints } = useEndpointStore();
  const navigate = useNavigate();

  const [selectedScenario, setSelectedScenario] = useState('');
  const [selectedEndpoint, setSelectedEndpoint] = useState('');
  const [starting, setStarting] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => { fetchBenchmarks(); fetchScenarios(); fetchEndpoints(); }, [fetchBenchmarks, fetchScenarios, fetchEndpoints]);

  // Poll for status updates every 3s
  useEffect(() => {
    const hasActive = benchmarks.some((b) => b.status === 'running' || b.status === 'pending');
    if (!hasActive) return;
    const interval = setInterval(fetchBenchmarks, 3000);
    return () => clearInterval(interval);
  }, [benchmarks, fetchBenchmarks]);

  const handleStart = async () => {
    if (!selectedScenario || !selectedEndpoint) return;
    setStarting(true);
    setActionError(null);
    try {
      const benchmark = await startBenchmark(selectedScenario, selectedEndpoint);
      navigate(`/benchmarks/${benchmark.id}`);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setStarting(false);
    }
  };

  const handleAbort = async (id) => {
    try {
      setActionError(null);
      await abortBenchmark(id);
    } catch (err) {
      setActionError(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      setActionError(null);
      await deleteBenchmark(id);
      setSelected((prev) => { const next = new Set(prev); next.delete(id); return next; });
    } catch (err) {
      setActionError(err.message);
    }
  };

  // Multi-select helpers
  const deletableIds = benchmarks
    .filter((b) => b.status !== 'running' && b.status !== 'pending')
    .map((b) => b.id);
  const allSelected = deletableIds.length > 0 && deletableIds.every((id) => selected.has(id));
  const someSelected = selected.size > 0;

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
    setConfirming(false);
  };

  const toggleSelectAll = () => {
    setSelected(allSelected ? new Set() : new Set(deletableIds));
    setConfirming(false);
  };

  const handleBulkDelete = async () => {
    if (!confirming) { setConfirming(true); return; }
    setBusy(true);
    setActionError(null);
    try {
      for (const id of selected) {
        await deleteBenchmark(id);
      }
      setSelected(new Set());
      setConfirming(false);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const formatDuration = (seconds) => {
    if (seconds == null) return '-';
    if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    if (seconds >= 60) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
    return `${Math.round(seconds)}s`;
  };

  const formatTime = (iso) => {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  if (loading && benchmarks.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading benchmarks...</p>
      </div>
    );
  }

  const cols = 'grid-cols-[40px_1fr_140px_120px_100px_80px_100px_160px]';

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-heading text-2xl font-bold">Benchmarks</h1>
      </div>

      {/* Start new benchmark */}
      <div className="mb-6 p-4 bg-surface-800 border border-surface-600 rounded-xl">
        <h2 className="font-heading text-sm uppercase tracking-wider text-gray-400 mb-3">Start New Benchmark</h2>
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Scenario</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="input w-full"
            >
              <option value="">Select a scenario...</option>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.total_users} users, {s.test_mode})
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">AI Endpoint</label>
            <select
              value={selectedEndpoint}
              onChange={(e) => setSelectedEndpoint(e.target.value)}
              className="input w-full"
            >
              <option value="">Select an endpoint...</option>
              {endpoints.map((ep) => (
                <option key={ep.id} value={ep.id}>
                  {ep.name} — {ep.model_name}{ep.gpu ? ` (${ep.gpu})` : ''}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handleStart}
            disabled={!selectedScenario || !selectedEndpoint || starting}
            className="px-5 py-2 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {starting ? 'Starting...' : 'Run Benchmark'}
          </button>
        </div>
      </div>

      {(error || actionError) && (
        <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
          {error || actionError}
        </div>
      )}

      {/* Bulk action bar */}
      {someSelected && (
        <div className="mb-2 flex items-center gap-3 px-4 py-2.5 bg-surface-800 border border-surface-600 rounded-lg">
          <span className="text-xs text-gray-400">{selected.size} selected</span>
          <div className="h-4 w-px bg-surface-600" />
          <button
            onClick={handleBulkDelete}
            disabled={busy}
            className={`px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 ${
              confirming
                ? 'bg-danger/20 text-danger hover:bg-danger/30'
                : 'bg-surface-700 text-gray-300 hover:text-danger hover:bg-surface-600'
            }`}
          >
            {confirming ? `Confirm Delete (${selected.size})` : `Delete (${selected.size})`}
          </button>
          <button
            onClick={() => { setSelected(new Set()); setConfirming(false); }}
            className="ml-auto px-2 py-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      {/* Benchmark list */}
      <div className="bg-surface-800 border border-surface-600 rounded-xl overflow-hidden">
        <div className={`grid ${cols} items-center px-4 py-2.5 border-b border-surface-600`}>
          <div className="flex items-center justify-center">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleSelectAll}
              className="accent-accent w-3.5 h-3.5 cursor-pointer"
              title="Select all completed"
            />
          </div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Scenario</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Endpoint</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Status</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Requests</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Duration</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Started</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-right">Actions</span>
        </div>

        {benchmarks.map((b) => {
          const isDeletable = b.status !== 'running' && b.status !== 'pending';
          return (
            <BenchmarkRow
              key={b.id}
              benchmark={b}
              cols={cols}
              isSelected={selected.has(b.id)}
              isDeletable={isDeletable}
              onToggle={() => toggleSelect(b.id)}
              formatDuration={formatDuration}
              formatTime={formatTime}
              onView={() => navigate(`/benchmarks/${b.id}`)}
              onAbort={() => handleAbort(b.id)}
              onDelete={() => handleDelete(b.id)}
            />
          );
        })}

        {benchmarks.length === 0 && (
          <div className="px-4 py-8 text-center text-gray-600 text-sm">
            No benchmarks yet. Select a scenario and endpoint, then click Run Benchmark.
          </div>
        )}
      </div>
    </div>
  );
}

function BenchmarkRow({ benchmark, cols, isSelected, isDeletable, onToggle, formatDuration, formatTime, onView, onAbort, onDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isActive = benchmark.status === 'running' || benchmark.status === 'pending';

  return (
    <div className={`grid ${cols} items-center px-4 py-3 border-b border-surface-600/50 last:border-b-0 transition-colors ${
      isSelected ? 'bg-accent/5' : 'hover:bg-surface-700/50'
    }`}>
      <div className="flex items-center justify-center">
        {isDeletable ? (
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onToggle}
            className="accent-accent w-3.5 h-3.5 cursor-pointer"
          />
        ) : (
          <div className="w-3.5 h-3.5" />
        )}
      </div>
      <div className="min-w-0 pr-4">
        <span className="text-sm text-gray-200 font-medium truncate block">
          {benchmark.scenario_name || 'Unknown Scenario'}
        </span>
        <span className="text-[10px] text-gray-600 font-mono">{benchmark.id.slice(0, 8)}</span>
      </div>
      <div className="min-w-0 text-center">
        <span className="text-xs text-gray-300 truncate block">{benchmark.endpoint_name || '-'}</span>
        {benchmark.model_name && (
          <span className="text-[10px] text-gray-600 truncate block">{benchmark.model_name}</span>
        )}
      </div>
      <div className="flex justify-center">
        <StatusBadge status={benchmark.status} />
      </div>
      <span className="text-xs text-gray-400 text-center tabular-nums">{benchmark.total_requests}</span>
      <span className="text-xs text-gray-400 text-center tabular-nums">{formatDuration(benchmark.duration_seconds)}</span>
      <span className="text-xs text-gray-400 text-center">{formatTime(benchmark.created_at)}</span>
      <div className="flex items-center justify-end gap-1.5">
        <button
          onClick={onView}
          className="px-2.5 py-1 text-[11px] rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
        >
          {isActive ? 'Live View' : 'Results'}
        </button>
        {isActive && (
          <button
            onClick={onAbort}
            className="px-2.5 py-1 text-[11px] rounded bg-warn/10 text-warn hover:bg-warn/20 transition-colors"
          >
            Abort
          </button>
        )}
        {!isActive && (
          confirmDelete ? (
            <button
              onClick={() => { onDelete(); setConfirmDelete(false); }}
              className="px-2.5 py-1 text-[11px] rounded bg-danger/20 text-danger hover:bg-danger/30 transition-colors"
            >
              Confirm
            </button>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="px-2.5 py-1 text-[11px] rounded bg-surface-700 text-gray-500 hover:text-danger hover:bg-surface-600 transition-colors"
            >
              Delete
            </button>
          )
        )}
      </div>
    </div>
  );
}
