import { useEffect, useRef, useState } from 'react';

const MAX_ENTRIES = 200;

export default function RequestLog({ snapshots, historicalRequests }) {
  const [entries, setEntries] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef(null);
  const lastCountRef = useRef(0);

  // Load historical requests when available (completed benchmarks)
  // Normalize from BenchmarkRequestRead format to the simplified format used by RequestRow
  useEffect(() => {
    if (!historicalRequests || historicalRequests.length === 0) return;
    setEntries(
      historicalRequests.map((req, i) => ({
        success: req.success !== undefined ? req.success : req.error_type == null,
        profile: req.profile || req.profile_name || 'unknown',
        turn: req.turn !== undefined ? req.turn : req.turn_number ?? 0,
        ttft_ms: req.ttft_ms != null ? Math.round(req.ttft_ms * 10) / 10 : null,
        tps: req.tps !== undefined ? req.tps : (req.tokens_per_second != null ? Math.round(req.tokens_per_second * 10) / 10 : null),
        output_tokens: req.output_tokens,
        http_status: req.http_status,
        error_type: req.error_type,
        key: `hist-${i}`,
      }))
    );
  }, [historicalRequests]);

  // Extract new recent_requests from incoming live snapshots
  useEffect(() => {
    if (snapshots.length <= lastCountRef.current) return;

    const newSnapshots = snapshots.slice(lastCountRef.current);
    lastCountRef.current = snapshots.length;

    const newEntries = [];
    for (const snap of newSnapshots) {
      if (snap.recent_requests) {
        for (const req of snap.recent_requests) {
          newEntries.push({
            ...req,
            key: `live-${snap.timestamp}-${newEntries.length}-${Math.random()}`,
          });
        }
      }
    }

    if (newEntries.length > 0) {
      setEntries((prev) => {
        const combined = [...prev, ...newEntries];
        return combined.length > MAX_ENTRIES
          ? combined.slice(combined.length - MAX_ENTRIES)
          : combined;
      });
    }
  }, [snapshots]);

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [entries, autoScroll]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(atBottom);
  };

  if (entries.length === 0) {
    return (
      <div className="mt-4 bg-surface-800 border border-surface-600 rounded-xl p-6 text-center text-gray-600 text-xs">
        No requests logged yet. Requests will appear here as the benchmark runs.
      </div>
    );
  }

  return (
    <div className="mt-4 bg-surface-800 border border-surface-600 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-surface-600">
        <h3 className="text-xs font-heading font-semibold uppercase tracking-wider text-gray-400">
          Request Log
        </h3>
        <div className="flex items-center gap-3">
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true);
                if (containerRef.current) {
                  containerRef.current.scrollTop = containerRef.current.scrollHeight;
                }
              }}
              className="text-[10px] text-accent hover:text-accent-bright transition-colors"
            >
              Jump to bottom
            </button>
          )}
          <span className="text-[10px] text-gray-600">
            {entries.length} requests
          </span>
        </div>
      </div>

      {/* Header row */}
      <div className="grid grid-cols-[80px_1fr_50px_80px_70px_70px_60px] gap-2 px-4 py-1.5 text-[10px] uppercase tracking-wider text-gray-600 border-b border-surface-700">
        <span>Status</span>
        <span>Profile</span>
        <span>Turn</span>
        <span>TTFT</span>
        <span>tok/s</span>
        <span>Tokens</span>
        <span>HTTP</span>
      </div>

      {/* Scrollable log */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="max-h-64 overflow-y-auto"
      >
        {entries.map((entry) => (
          <RequestRow key={entry.key} entry={entry} />
        ))}
      </div>
    </div>
  );
}

function RequestRow({ entry }) {
  const statusIcon = entry.success ? (
    <span className="text-green-400">&#10003;</span>
  ) : (
    <span className="text-danger">&#10007;</span>
  );

  const statusLabel = entry.success ? (
    <span className="text-green-400/80">OK</span>
  ) : (
    <span className="text-danger/80">{entry.error_type || 'error'}</span>
  );

  return (
    <div className="grid grid-cols-[80px_1fr_50px_80px_70px_70px_60px] gap-2 px-4 py-1 text-xs font-mono border-b border-surface-700/50 hover:bg-surface-700/30 transition-colors">
      <span className="flex items-center gap-1.5">
        {statusIcon}
        <span className="truncate">{statusLabel}</span>
      </span>
      <span className="text-gray-300 truncate">{entry.profile}</span>
      <span className="text-gray-500">T{entry.turn + 1}</span>
      <span className={entry.success ? 'text-gray-200' : 'text-gray-600'}>
        {entry.ttft_ms != null ? `${entry.ttft_ms} ms` : '-'}
      </span>
      <span className={entry.success ? 'text-gray-200' : 'text-gray-600'}>
        {entry.tps != null ? entry.tps : '-'}
      </span>
      <span className="text-gray-400">
        {entry.output_tokens != null ? entry.output_tokens : '-'}
      </span>
      <span className={entry.http_status && entry.http_status >= 400 ? 'text-danger' : 'text-gray-500'}>
        {entry.http_status || '-'}
      </span>
    </div>
  );
}
