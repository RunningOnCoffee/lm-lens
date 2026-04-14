import InfoTip from '../InfoTip';

function qualityColor(score) {
  if (score >= 0.9) return 'text-green-400';
  if (score >= 0.7) return 'text-accent';
  if (score >= 0.5) return 'text-warn';
  return 'text-danger';
}

function qualityBg(score) {
  if (score >= 0.9) return 'bg-green-400';
  if (score >= 0.7) return 'bg-accent';
  if (score >= 0.5) return 'bg-warn';
  return 'bg-danger';
}

export default function EndpointQualityChart({ endpoints }) {
  const withQuality = (endpoints || []).filter((ep) => ep.avg_quality_overall != null);
  if (withQuality.length === 0) return null;

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
      <h3 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3 inline-flex items-center gap-1.5">
        Quality by Endpoint
        <InfoTip text="Average quality score per endpoint across all runs. Based on heuristic checks: completeness, compliance, coherence, safety." />
      </h3>
      <div className="space-y-3">
        {withQuality.map((ep) => {
          const pct = Math.round(ep.avg_quality_overall * 100);
          return (
            <div key={ep.endpoint_id}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-300">{ep.name}</span>
                <span className={`text-xs font-mono font-medium ${qualityColor(ep.avg_quality_overall)}`}>{pct}%</span>
              </div>
              <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${qualityBg(ep.avg_quality_overall)} transition-all`}
                  style={{ width: `${pct}%`, opacity: pct > 0 ? 1 : 0 }}
                />
              </div>
              <div className="text-[10px] text-gray-600 mt-0.5">
                {ep.model_name}{ep.run_count > 1 ? ` — ${ep.run_count} runs` : ' — 1 run'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
