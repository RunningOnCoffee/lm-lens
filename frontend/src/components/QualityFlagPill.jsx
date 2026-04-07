const FLAG_STYLES = {
  truncated: 'bg-warn/20 text-warn border-warn/30',
  empty: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  refusal: 'bg-danger/20 text-danger border-danger/30',
  repeated_tokens: 'bg-purple-400/20 text-purple-400 border-purple-400/30',
};

const FLAG_LABELS = {
  truncated: 'Truncated',
  empty: 'Empty',
  refusal: 'Refusal',
  repeated_tokens: 'Repeated',
};

export default function QualityFlagPill({ flag }) {
  const style = FLAG_STYLES[flag] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  const label = FLAG_LABELS[flag] || flag;

  return (
    <span className={`inline-block px-1.5 py-0.5 text-[10px] rounded border font-medium ${style}`}>
      {label}
    </span>
  );
}
