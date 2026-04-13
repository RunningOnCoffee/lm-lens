import { useEffect, useState } from 'react';
import { benchmarksApi } from '../api/client';
import InfoTip from './InfoTip';
import QualityFlagPill from './QualityFlagPill';

const DIMENSION_META = {
  completeness: {
    label: 'Completeness',
    tip: 'Measures whether the LLM produced a full response. Penalised by empty or truncated outputs.',
    color: 'bg-green-400',
    colorText: 'text-green-400',
  },
  compliance: {
    label: 'Compliance',
    tip: 'Measures whether the response matches the requested format (JSON, bullet list, code block) and length constraints.',
    color: 'bg-sky-400',
    colorText: 'text-sky-400',
  },
  coherence: {
    label: 'Coherence',
    tip: 'Measures response quality signals like language consistency and token diversity. Penalised by repeated tokens or wrong language.',
    color: 'bg-purple-400',
    colorText: 'text-purple-400',
  },
  safety: {
    label: 'Safety',
    tip: 'Measures whether the LLM answered the prompt instead of refusing. Penalised by refusal responses.',
    color: 'bg-amber-400',
    colorText: 'text-amber-400',
  },
};

const DIMENSION_ORDER = ['completeness', 'compliance', 'coherence', 'safety'];

function overallColor(score) {
  if (score >= 0.9) return 'text-green-400';
  if (score >= 0.7) return 'text-accent';
  if (score >= 0.5) return 'text-warn';
  return 'text-danger';
}

function overallBg(score) {
  if (score >= 0.9) return 'border-green-400/30';
  if (score >= 0.7) return 'border-accent/30';
  if (score >= 0.5) return 'border-warn/30';
  return 'border-danger/30';
}

export default function QualityScorecard({ benchmarkId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await benchmarksApi.qualityScores(benchmarkId);
        if (!cancelled) setData(res.data);
      } catch {
        // no quality data available
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [benchmarkId]);

  if (loading || !data || !data.overall) return null;

  const { overall, by_profile, flag_distribution, scored_requests, flagged_requests } = data;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4 mb-4">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold">Quality Scorecard</h3>
        <InfoTip text="Quality scores are computed from heuristic checks on each LLM response. Dimensions: Completeness (not empty/truncated), Compliance (correct format/length), Coherence (no repetition/language mismatch), Safety (not refused). Overall is a weighted average." />
        <span className="text-[10px] text-gray-600 font-mono ml-auto">
          {scored_requests} responses scored
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-4">
        {/* Left: Overall score */}
        <div className={`flex flex-col items-center justify-center px-6 py-3 border rounded-lg bg-surface-900/50 ${overallBg(overall.overall)}`}>
          <div className={`text-3xl font-mono font-bold ${overallColor(overall.overall)}`}>
            {Math.round(overall.overall * 100)}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-gray-500 mt-0.5">Overall</div>
        </div>

        {/* Right: Dimension bars */}
        <div className="space-y-2">
          {DIMENSION_ORDER.map((dim) => {
            const meta = DIMENSION_META[dim];
            const score = overall[dim] ?? 0;
            const pct = Math.round(score * 100);
            return (
              <div key={dim} className="flex items-center gap-2">
                <div className="w-24 text-[11px] text-gray-400 flex items-center gap-1">
                  {meta.label}
                  <InfoTip text={meta.tip} />
                </div>
                <div className="flex-1 h-4 bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${meta.color} transition-all duration-500`}
                    style={{ width: `${pct}%`, opacity: pct > 0 ? 1 : 0 }}
                  />
                </div>
                <div className={`w-10 text-right text-xs font-mono ${meta.colorText}`}>
                  {pct}%
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Flag distribution */}
      {Object.keys(flag_distribution).length > 0 && (
        <div className="mt-4 pt-3 border-t border-surface-600">
          <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-2">
            Flag Distribution
            <span className="text-gray-700 ml-2">
              {flagged_requests} of {scored_requests} responses flagged
            </span>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5">
            {Object.entries(flag_distribution).map(([flag, info]) => (
              <div key={flag} className="flex items-center gap-1.5">
                <QualityFlagPill flag={flag} />
                <span className="text-xs font-mono text-gray-400">{info.count}</span>
                <span className="text-[10px] text-gray-600">({info.pct}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per-profile breakdown */}
      {Object.keys(by_profile).length > 1 && (
        <div className="mt-4 pt-3 border-t border-surface-600">
          <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-2">Per-Profile Quality</div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-600 text-[10px] uppercase tracking-wider">
                  <th className="text-left py-1 pr-4">Profile</th>
                  {DIMENSION_ORDER.map((dim) => (
                    <th key={dim} className="text-right py-1 px-2">{DIMENSION_META[dim].label}</th>
                  ))}
                  <th className="text-right py-1 pl-2">Overall</th>
                  <th className="text-right py-1 pl-2">N</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(by_profile).map(([pid, info]) => (
                  <tr key={pid} className="border-t border-surface-700">
                    <td className="py-1.5 pr-4 text-gray-300">{info.profile_name}</td>
                    {DIMENSION_ORDER.map((dim) => {
                      const val = info.scores[dim] ?? 0;
                      return (
                        <td key={dim} className={`text-right py-1.5 px-2 font-mono ${val < 0.7 ? 'text-warn' : 'text-gray-400'}`}>
                          {Math.round(val * 100)}%
                        </td>
                      );
                    })}
                    <td className={`text-right py-1.5 pl-2 font-mono font-medium ${overallColor(info.scores.overall ?? 0)}`}>
                      {Math.round((info.scores.overall ?? 0) * 100)}%
                    </td>
                    <td className="text-right py-1.5 pl-2 font-mono text-gray-600">
                      {info.scored_requests}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
