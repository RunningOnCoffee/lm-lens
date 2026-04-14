import InfoTip from './InfoTip';

export default function MetricCard({ label, value, subtitle, color, tooltip }) {
  const textColor =
    color === 'danger' ? 'text-danger' :
    color === 'ok' ? 'text-green-400' :
    'text-gray-100';

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-3">
      <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 inline-flex items-center gap-1">
        {label}
        {tooltip && <InfoTip text={tooltip} />}
      </div>
      <div className={`text-lg font-mono font-semibold ${textColor}`}>{value}</div>
      {subtitle && (
        <div className="text-[9px] text-gray-600 mt-0.5">{subtitle}</div>
      )}
    </div>
  );
}
