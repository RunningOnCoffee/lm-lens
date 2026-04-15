import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useBenchmarkStore from '../stores/benchmarkStore';
import useScenarioStore from '../stores/scenarioStore';
import useEndpointStore from '../stores/endpointStore';
import InfoTip from '../components/InfoTip';
import Spinner from '../components/Spinner';
import StatusBadge from '../components/StatusBadge';

export default function Benchmarks() {
  const { benchmarks, loading, error, fetchBenchmarks, startBenchmark, deleteBenchmark, abortBenchmark } = useBenchmarkStore();
  const { scenarios, fetchScenarios } = useScenarioStore();
  const { endpoints, fetchEndpoints } = useEndpointStore();
  const navigate = useNavigate();

  const [selectedScenario, setSelectedScenario] = useState('');
  const [selectedEndpoint, setSelectedEndpoint] = useState('');
  const [seedInput, setSeedInput] = useState('');
  const [starting, setStarting] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [compareSelected, setCompareSelected] = useState(new Set());
  const [concurrentWarning, setConcurrentWarning] = useState(null); // { conflicts: [...] }

  useEffect(() => { fetchBenchmarks(); fetchScenarios(); fetchEndpoints(); }, [fetchBenchmarks, fetchScenarios, fetchEndpoints]);

  // Poll for status updates every 3s
  useEffect(() => {
    const hasActive = benchmarks.some((b) => b.status === 'running' || b.status === 'pending');
    if (!hasActive) return;
    const interval = setInterval(fetchBenchmarks, 3000);
    return () => clearInterval(interval);
  }, [benchmarks, fetchBenchmarks]);

  const doStart = async () => {
    setStarting(true);
    setActionError(null);
    try {
      const seed = seedInput.trim()
        ? parseInt(seedInput.trim(), 10)
        : Math.floor(1000 + Math.random() * 9000); // Auto-generate 4-digit seed
      const benchmark = await startBenchmark(selectedScenario, selectedEndpoint, isNaN(seed) ? undefined : seed);
      navigate(`/benchmarks/${benchmark.id}`);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setStarting(false);
    }
  };

  const handleStart = () => {
    if (!selectedScenario || !selectedEndpoint) return;
    // Check if any running/pending benchmarks target the same endpoint
    const conflicts = benchmarks.filter(
      (b) => (b.status === 'running' || b.status === 'pending') &&
        b.endpoint_id === selectedEndpoint
    );
    if (conflicts.length > 0) {
      setConcurrentWarning({ conflicts });
    } else {
      doStart();
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

  // Compare mode helpers
  const toggleCompareSelect = (id) => {
    setCompareSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < 2) {
        next.add(id);
      }
      return next;
    });
  };

  const exitCompareMode = () => {
    setCompareMode(false);
    setCompareSelected(new Set());
  };

  const handleCompare = () => {
    const [a, b] = [...compareSelected];
    navigate(`/benchmarks/compare?a=${a}&b=${b}`);
  };

  const completedCount = benchmarks.filter((b) => b.status !== 'running' && b.status !== 'pending').length;

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
        <div className="flex items-center gap-2 text-gray-500"><Spinner size="sm" /> Loading benchmarks...</div>
      </div>
    );
  }

  const cols = 'grid-cols-[40px_1fr_140px_60px_120px_100px_80px_100px_190px]';

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-heading text-2xl font-bold">Benchmarks</h1>
        {!compareMode && completedCount >= 2 && (
          <button
            onClick={() => { setCompareMode(true); setSelected(new Set()); setConfirming(false); }}
            className="px-4 py-2 text-sm rounded-lg bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 hover:text-accent-bright transition-colors font-medium"
          >
            Compare Runs
          </button>
        )}
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
          <div className="w-36">
            <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1">
              Seed
              <span className="text-gray-600">(optional)</span>
              <InfoTip text="Use the same seed + scenario to get identical prompts across runs, enabling fair side-by-side comparison of different endpoints." />
            </label>
            <div className="flex items-center gap-1">
              <input
                type="text"
                inputMode="numeric"
                value={seedInput}
                onChange={(e) => setSeedInput(e.target.value.replace(/[^0-9]/g, ''))}
                placeholder="Random"
                className="input w-full text-center"
              />
              <button
                type="button"
                onClick={() => setSeedInput(String(Math.floor(Math.random() * 100000)))}
                className="px-1.5 py-1.5 text-[10px] rounded bg-surface-700 text-gray-400 hover:text-gray-200 hover:bg-surface-600 transition-colors flex-shrink-0"
                title="Generate random seed"
              >
                🎲
              </button>
            </div>
          </div>
          <button
            onClick={handleStart}
            disabled={!selectedScenario || !selectedEndpoint || starting}
            className="px-5 py-2 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap self-end"
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

      {/* Concurrent benchmark warning dialog */}
      {concurrentWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-surface-800 border border-warn/30 rounded-xl shadow-2xl max-w-md w-full mx-4 p-6">
            <div className="flex items-start gap-3 mb-4">
              <div className="text-warn text-xl mt-0.5">&#9888;</div>
              <div>
                <h3 className="font-heading text-base font-semibold text-gray-100 mb-1">
                  Endpoint Already Under Load
                </h3>
                <p className="text-sm text-gray-400">
                  {concurrentWarning.conflicts.length === 1
                    ? 'There is already a benchmark running on this endpoint. '
                    : `There are ${concurrentWarning.conflicts.length} benchmarks running on this endpoint. `}
                  Running concurrent benchmarks against the same endpoint will cause them to compete for resources, which can falsify performance results.
                </p>
              </div>
            </div>
            <div className="mb-5 space-y-1.5">
              {concurrentWarning.conflicts.map((b) => (
                <div key={b.id} className="flex items-center gap-2 px-3 py-2 bg-surface-700/50 rounded-lg text-xs">
                  <StatusBadge status={b.status} />
                  <span className="text-gray-300 truncate">{b.scenario_name || 'Unknown'}</span>
                  <span className="text-gray-600 font-mono ml-auto">{b.id.slice(0, 8)}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConcurrentWarning(null)}
                className="px-4 py-2 text-sm rounded-lg bg-surface-700 text-gray-300 hover:bg-surface-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setConcurrentWarning(null); doStart(); }}
                className="px-4 py-2 text-sm rounded-lg bg-warn/20 border border-warn/30 text-warn hover:bg-warn/30 transition-colors font-medium"
              >
                Run Anyway
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Compare mode banner */}
      {compareMode && (
        <div className="mb-3 flex items-center gap-3 px-4 py-3 bg-accent/5 border border-accent/30 rounded-xl">
          <div className="flex-1">
            <div className="text-sm text-accent font-medium">
              {compareSelected.size === 0 && 'Select 2 benchmarks to compare'}
              {compareSelected.size === 1 && 'Select 1 more benchmark'}
              {compareSelected.size === 2 && 'Ready to compare'}
            </div>
            <div className="text-[11px] text-gray-500 mt-0.5">
              Click on completed benchmarks to select them for comparison
            </div>
          </div>
          {compareSelected.size === 2 && (
            <button
              onClick={handleCompare}
              className="px-5 py-2 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors"
            >
              Compare Now
            </button>
          )}
          <button
            onClick={exitCompareMode}
            className="px-3 py-1.5 text-xs text-danger/70 border border-danger/30 rounded-lg hover:bg-danger/10 hover:text-danger transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Bulk action bar */}
      {!compareMode && someSelected && (
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
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Seed</span>
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
              compareMode={compareMode}
              compareSelected={compareSelected.has(b.id)}
              compareSelectable={isDeletable && (compareSelected.size < 2 || compareSelected.has(b.id))}
              onCompareToggle={() => toggleCompareSelect(b.id)}
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

function BenchmarkRow({ benchmark, cols, isSelected, isDeletable, onToggle, compareMode, compareSelected, compareSelectable, onCompareToggle, formatDuration, formatTime, onView, onAbort, onDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [aborting, setAborting] = useState(false);
  const isActive = benchmark.status === 'running' || benchmark.status === 'pending';

  const rowBg = compareMode
    ? compareSelected
      ? 'bg-accent/10 border-l-2 border-l-accent'
      : compareSelectable
        ? 'hover:bg-surface-700/50 cursor-pointer'
        : 'opacity-40'
    : isSelected
      ? 'bg-accent/5'
      : 'hover:bg-surface-700/50';

  return (
    <div
      className={`grid ${cols} items-center px-4 py-3 border-b border-surface-600/50 last:border-b-0 transition-colors ${rowBg}`}
      onClick={compareMode && compareSelectable ? onCompareToggle : undefined}
    >
      <div className="flex items-center justify-center">
        {compareMode ? (
          compareSelectable ? (
            <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ${
              compareSelected ? 'border-accent bg-accent' : 'border-gray-500'
            }`}>
              {compareSelected && <span className="text-surface-900 text-[9px] font-bold">&#10003;</span>}
            </div>
          ) : (
            <div className="w-4 h-4" />
          )
        ) : isDeletable ? (
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
      <span className="text-xs text-gray-500 text-center font-mono">
        {benchmark.seed != null ? benchmark.seed : '-'}
      </span>
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
            onClick={() => { setAborting(true); onAbort(); }}
            disabled={aborting}
            className="px-2.5 py-1 text-[11px] rounded bg-warn/10 text-warn hover:bg-warn/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {aborting ? 'Aborting...' : 'Abort'}
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
