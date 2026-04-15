import { useState, useEffect, useCallback, useMemo } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { benchmarksApi } from '../api/client';
import QualityFlagPill from './QualityFlagPill';
import Spinner from './Spinner';

const PER_PAGE = 20;

function formatMs(v) {
  if (v == null) return '-';
  if (v >= 10000) return `${(v / 1000).toFixed(2)}s`;
  return `${v.toFixed(0)}ms`;
}

export default function ResponseBrowser({ benchmarkId }) {
  const [sessions, setSessions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [profiles, setProfiles] = useState([]);
  const [filterProfile, setFilterProfile] = useState('');
  const [expandedSession, setExpandedSession] = useState(null);

  // Fetch profile list for filter
  useEffect(() => {
    benchmarksApi.profileStats(benchmarkId).then((res) => {
      setProfiles(res.data || []);
    }).catch(() => {});
  }, [benchmarkId]);

  // Fetch sessions
  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, per_page: PER_PAGE };
      if (filterProfile) params.profile_id = filterProfile;
      const res = await benchmarksApi.sessions(benchmarkId, params);
      setSessions(res.data);
      setTotal(res.meta.total);
    } catch {
      setSessions([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [benchmarkId, page, filterProfile]);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);
  useEffect(() => { setPage(1); }, [filterProfile]);

  const totalPages = Math.ceil(total / PER_PAGE);

  const profileOptions = useMemo(() =>
    (profiles || []).map((p) => ({ id: p.profile_id, name: p.profile_name })),
    [profiles]
  );

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-[10px] uppercase tracking-wider text-gray-600">Filter:</span>
        <select
          value={filterProfile}
          onChange={(e) => setFilterProfile(e.target.value)}
          className="text-xs bg-surface-700 border border-surface-600 rounded px-2 py-1 text-gray-300 focus:outline-none focus:border-accent/50"
        >
          <option value="">All Profiles</option>
          {profileOptions.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <span className="ml-auto text-[10px] text-gray-600">
          {total} conversation{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Session list */}
      {loading && sessions.length === 0 ? (
        <div className="bg-surface-800 border border-surface-600 rounded-xl p-12 flex items-center justify-center gap-2 text-gray-500 text-sm">
          <Spinner size="sm" /> Loading conversations...
        </div>
      ) : sessions.length === 0 ? (
        <div className="bg-surface-800 border border-surface-600 rounded-xl p-12 text-center text-gray-500 text-sm">
          No conversations found.
        </div>
      ) : (
        sessions.map((s) => (
          <SessionCard
            key={s.session_id}
            session={s}
            benchmarkId={benchmarkId}
            isExpanded={expandedSession === s.session_id}
            onToggle={() => setExpandedSession(
              expandedSession === s.session_id ? null : s.session_id
            )}
          />
        ))
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-1 py-1">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="text-xs text-gray-400 hover:text-gray-200 disabled:text-gray-700 disabled:cursor-not-allowed"
          >
            ← Previous
          </button>
          <span className="text-[10px] text-gray-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="text-xs text-gray-400 hover:text-gray-200 disabled:text-gray-700 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

function SessionCard({ session, benchmarkId, isExpanded, onToggle }) {
  const s = session;
  const hasErrors = s.error_count > 0;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl overflow-hidden">
      {/* Session header — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 px-4 py-3 hover:bg-surface-700/30 transition-colors text-left"
      >
        <span className="text-gray-500 text-xs w-5">
          {isExpanded ? '▾' : '▸'}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-200 font-medium">{s.profile_name}</span>
            <span className="font-mono text-[10px] text-gray-600">{s.session_id.slice(0, 8)}</span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-[11px] text-gray-500">
            <span>{s.turn_count} turn{s.turn_count !== 1 ? 's' : ''}</span>
            <span>·</span>
            <span>TTFT {formatMs(s.first_ttft_ms)}</span>
            <span>·</span>
            <span>{s.avg_tps != null ? `${s.avg_tps} tok/s` : '-'}</span>
            <span>·</span>
            <span>{(s.total_output_tokens || 0).toLocaleString()} tokens</span>
            {hasErrors && (
              <>
                <span>·</span>
                <span className="text-danger">{s.error_count} error{s.error_count !== 1 ? 's' : ''}</span>
              </>
            )}
          </div>
        </div>

        {s.quality_flags && s.quality_flags.length > 0 && (
          <div className="flex items-center gap-1 flex-shrink-0">
            {s.quality_flags.map((f) => <QualityFlagPill key={f} flag={f} />)}
          </div>
        )}

        <span className={`flex-shrink-0 w-2 h-2 rounded-full ${hasErrors ? 'bg-danger' : 'bg-green-400/60'}`} />
      </button>

      {/* Expanded: conversation view */}
      {isExpanded && (
        <ConversationView benchmarkId={benchmarkId} sessionId={s.session_id} />
      )}
    </div>
  );
}

function ConversationView({ benchmarkId, sessionId }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    benchmarksApi.requests(benchmarkId, {
      session_id: sessionId,
      sort_by: 'turn_number',
      sort_dir: 'asc',
      per_page: 200,
    }).then((res) => {
      if (!cancelled) {
        setRequests(res.data);
        setLoading(false);
      }
    }).catch(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [benchmarkId, sessionId]);

  if (loading) {
    return (
      <div className="px-6 py-8 flex items-center justify-center gap-2 text-gray-500 text-sm border-t border-surface-600">
        <Spinner size="sm" /> Loading conversation...
      </div>
    );
  }

  return (
    <div className="border-t border-surface-600 px-4 py-4 space-y-3">
      {requests.map((req, i) => (
        <TurnBubble key={req.id || i} request={req} turnIndex={i} />
      ))}
    </div>
  );
}

function TurnBubble({ request, turnIndex }) {
  const [showDetails, setShowDetails] = useState(false);
  const r = request;
  const isError = r.error_type != null;

  // Extract user message from request body
  const userMessage = useMemo(() => {
    if (!r.request_body?.messages) return null;
    const msgs = r.request_body.messages;
    // Last user message is the prompt for this turn
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') return msgs[i].content;
    }
    return null;
  }, [r.request_body]);

  return (
    <div className="space-y-2">
      {/* Turn header with metrics */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-600">
          Turn {turnIndex + 1}
        </span>
        <div className="flex-1 h-px bg-surface-600" />
        <div className="flex items-center gap-2 text-[10px] text-gray-500">
          <span>TTFT {formatMs(r.ttft_ms)}</span>
          <span className="text-gray-700">|</span>
          <span>{r.tokens_per_second != null ? `${r.tokens_per_second.toFixed(1)} tok/s` : '-'}</span>
          <span className="text-gray-700">|</span>
          <span>{r.output_tokens ?? 0} tokens</span>
          {r.quality_flags && r.quality_flags.length > 0 && (
            <>
              <span className="text-gray-700">|</span>
              {r.quality_flags.map((f) => <QualityFlagPill key={f} flag={f} />)}
            </>
          )}
          {isError && (
            <>
              <span className="text-gray-700">|</span>
              <span className="text-danger">{r.error_type}</span>
            </>
          )}
        </div>
      </div>

      {/* User message */}
      {userMessage && (
        <div className="flex justify-start">
          <div className="max-w-[85%] bg-surface-700 border border-surface-600 rounded-lg rounded-tl-sm px-3 py-2">
            <div className="text-[9px] uppercase tracking-wider text-gray-600 mb-1">User</div>
            <div className="text-xs text-gray-300 whitespace-pre-wrap break-words leading-relaxed">
              {typeof userMessage === 'string'
                ? (userMessage.length > 800 ? userMessage.slice(0, 800) + '…' : userMessage)
                : JSON.stringify(userMessage)}
            </div>
          </div>
        </div>
      )}

      {/* LLM response */}
      {r.response_text ? (
        <div className="flex justify-end">
          <div className="max-w-[85%] bg-accent/5 border border-accent/20 rounded-lg rounded-tr-sm px-3 py-2">
            <div className="text-[9px] uppercase tracking-wider text-accent/50 mb-1">Assistant</div>
            <div className="text-xs text-gray-200 break-words leading-relaxed markdown-body">
              <Markdown
                remarkPlugins={[remarkGfm]}
                components={{
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
                }}
              >
                {r.response_text.length > 2000
                  ? r.response_text.slice(0, 2000) + '\n\n…'
                  : r.response_text}
              </Markdown>
            </div>
          </div>
        </div>
      ) : isError ? (
        <div className="flex justify-end">
          <div className="max-w-[85%] bg-danger/5 border border-danger/20 rounded-lg rounded-tr-sm px-3 py-2">
            <div className="text-[9px] uppercase tracking-wider text-danger/50 mb-1">Error</div>
            <div className="text-xs text-danger/80 whitespace-pre-wrap break-words">
              {r.error_detail || r.error_type || 'Unknown error'}
            </div>
          </div>
        </div>
      ) : null}

      {/* Details toggle */}
      <div className="flex justify-start">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-[10px] text-gray-600 hover:text-gray-400 transition-colors"
        >
          {showDetails ? '▾ Hide details' : '▸ Show details'}
        </button>
      </div>

      {showDetails && (
        <div className="ml-4 space-y-2 text-xs">
          {/* Metrics detail */}
          <div className="flex items-center gap-4 flex-wrap text-[11px]">
            <Detail label="TTFT" value={formatMs(r.ttft_ms)} />
            <Detail label="TGT" value={formatMs(r.tgt_ms)} />
            <Detail label="tok/s" value={r.tokens_per_second?.toFixed(1)} />
            <Detail label="Input" value={r.input_tokens} />
            <Detail label="Output" value={r.output_tokens} />
            <Detail label="HTTP" value={r.http_status} />
            <Detail label="Model" value={r.model_reported} />
          </div>

          {/* Request body */}
          {r.request_body && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">Request Body</div>
              <div className="bg-surface-800 border border-surface-600 rounded p-2 text-gray-400 font-mono text-[10px] whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                {JSON.stringify(r.request_body, null, 2)}
              </div>
            </div>
          )}

          {/* ITL sparkline */}
          {r.inter_token_latencies && r.inter_token_latencies.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">
                Inter-Token Latencies ({r.inter_token_latencies.length} tokens)
              </div>
              <ITLSparkline values={r.inter_token_latencies} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }) {
  if (value == null) return null;
  return (
    <span>
      <span className="text-gray-600">{label}: </span>
      <span className="text-gray-300">{String(value)}</span>
    </span>
  );
}

function ITLSparkline({ values }) {
  const maxVal = Math.max(...values);
  const width = Math.min(values.length * 2, 600);
  const height = 40;
  const barWidth = Math.max(1, (width / values.length) - 0.5);

  return (
    <svg width={width} height={height} className="bg-surface-800 rounded border border-surface-600">
      {values.map((v, i) => {
        const barH = maxVal > 0 ? (v / maxVal) * (height - 4) : 0;
        const x = (i / values.length) * width;
        return (
          <rect
            key={i}
            x={x}
            y={height - 2 - barH}
            width={barWidth}
            height={barH}
            fill="#00d4ff"
            opacity={0.6}
          />
        );
      })}
    </svg>
  );
}
