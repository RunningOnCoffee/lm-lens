const STATUS_STYLES = {
  pending:   'bg-gray-500/20 text-gray-400',
  running:   'bg-accent/20 text-accent',
  completed: 'bg-green-500/20 text-green-400',
  aborted:   'bg-warn/20 text-warn',
  failed:    'bg-danger/20 text-danger',
};

export default function StatusBadge({ status }) {
  return (
    <span className={`px-2 py-0.5 text-[11px] rounded-full font-medium ${STATUS_STYLES[status] || STATUS_STYLES.pending}`}>
      {status}
    </span>
  );
}
