// Shared chart theme constants matching Tailwind config
export const COLORS = {
  accent: '#00d4ff',
  accentDim: '#00a3c7',
  accentBright: '#40e0ff',
  warn: '#f59e0b',
  danger: '#ef4444',
  green: '#4ade80',
  purple: '#a78bfa',
  pink: '#f472b6',
  orange: '#fb923c',
  surface600: '#252a3a',
  surface700: '#1c2030',
  surface800: '#141720',
  gray400: '#9ca3af',
  gray500: '#6b7280',
  gray600: '#4b5563',
};

// Profile color palette for per-profile breakdowns
export const PROFILE_COLORS = [
  '#00d4ff', '#f59e0b', '#a78bfa', '#4ade80',
  '#f472b6', '#fb923c', '#38bdf8', '#facc15',
];

export const AXIS_STYLE = {
  fontSize: 10,
  fontFamily: 'JetBrains Mono, monospace',
  fill: '#6b7280',
};

export const GRID_STYLE = {
  stroke: '#252a3a',
  strokeDasharray: '3 3',
};

export const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: '#141720',
    border: '1px solid #252a3a',
    borderRadius: 8,
    fontSize: 11,
    fontFamily: 'JetBrains Mono, monospace',
  },
  labelStyle: { color: '#6b7280', fontSize: 10 },
  itemStyle: { padding: '1px 0' },
};
