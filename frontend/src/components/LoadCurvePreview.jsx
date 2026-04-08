import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from './charts/ChartTheme';

/**
 * Client-side load curve preview — mirrors backend load_curves.py formulas.
 */

function computeStep(elapsed, totalUsers, _duration, config) {
  const stepSize = config.ramp_users_per_step || 1;
  const interval = config.ramp_interval_seconds || 10;
  const stepsCompleted = Math.floor(elapsed / interval) + 1;
  return Math.max(1, Math.min(stepsCompleted * stepSize, totalUsers));
}

function computeLinear(elapsed, totalUsers, duration) {
  if (duration <= 0) return totalUsers;
  const progress = Math.min(elapsed / duration, 1.0);
  return Math.max(1, Math.min(Math.round(1 + (totalUsers - 1) * progress), totalUsers));
}

function computeSpike(elapsed, totalUsers, duration, config) {
  if (duration <= 0) return totalUsers;
  const baseFraction = 0.2;
  const base = Math.max(1, Math.round(totalUsers * baseFraction));
  const spikeAtPct = config.spike_at_pct ?? 50;
  const spikeDuration = config.spike_duration_seconds ?? 10;
  const spikeStart = duration * (spikeAtPct / 100);
  const spikeEnd = spikeStart + spikeDuration;
  if (elapsed >= spikeStart && elapsed < spikeEnd) return totalUsers;
  return base;
}

function computeWave(elapsed, totalUsers, _duration, config) {
  const period = config.wave_period_seconds || 30;
  const minFraction = 0.2;
  const sinVal = Math.sin((2 * Math.PI * elapsed) / period - Math.PI / 2);
  const fraction = minFraction + (1 - minFraction) * (sinVal + 1) / 2;
  return Math.max(1, Math.min(Math.round(totalUsers * fraction), totalUsers));
}

const CURVE_COMPUTERS = {
  step: computeStep,
  linear: computeLinear,
  spike: computeSpike,
  wave: computeWave,
};

export default function LoadCurvePreview({ loadConfig, totalUsers }) {
  const duration = loadConfig.duration_seconds || 60;
  const curveType = loadConfig.load_curve || 'step';
  const compute = CURVE_COMPUTERS[curveType] || computeStep;

  const data = useMemo(() => {
    if (totalUsers <= 0) return [];
    // Generate one point per second, cap at 300 points for performance
    const points = Math.min(duration, 300);
    const step = duration / points;
    const result = [];
    for (let i = 0; i <= points; i++) {
      const t = i * step;
      result.push({
        time: Math.round(t),
        users: compute(t, totalUsers, duration, loadConfig),
      });
    }
    return result;
  }, [curveType, totalUsers, duration, loadConfig.ramp_users_per_step, loadConfig.ramp_interval_seconds, loadConfig.spike_at_pct, loadConfig.spike_duration_seconds, loadConfig.wave_period_seconds]);

  if (totalUsers <= 0) {
    return (
      <div className="h-28 flex items-center justify-center text-xs text-gray-600">
        Add profiles to see the load curve preview
      </div>
    );
  }

  const formatTime = (seconds) => {
    if (seconds >= 60) return `${Math.floor(seconds / 60)}m${seconds % 60 ? `${seconds % 60}s` : ''}`;
    return `${seconds}s`;
  };

  return (
    <div className="h-28">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
          <CartesianGrid {...GRID_STYLE} />
          <XAxis
            dataKey="time"
            {...AXIS_STYLE}
            tickFormatter={formatTime}
            interval="preserveStartEnd"
          />
          <YAxis
            {...AXIS_STYLE}
            domain={[0, totalUsers]}
            allowDecimals={false}
          />
          <Tooltip
            {...TOOLTIP_STYLE}
            formatter={(value) => [`${value} users`, 'Active Users']}
            labelFormatter={(label) => formatTime(label)}
          />
          <Area
            type="stepAfter"
            dataKey="users"
            stroke={COLORS.accent}
            fill={COLORS.accent}
            fillOpacity={0.15}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
