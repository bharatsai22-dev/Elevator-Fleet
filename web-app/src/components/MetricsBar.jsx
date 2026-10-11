import React from 'react';

/**
 * KPI cards. Exported separately so pages (e.g. Analytics) can reuse MetricCard.
 */

const COLORS = {
  amber:  { bg: 'rgba(251,191,36,0.08)', border: 'rgba(251,191,36,0.25)', text: 'text-amber-400',   glow: '0 0 20px rgba(251,191,36,0.12)' },
  green:  { bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.25)', text: 'text-emerald-400', glow: '0 0 20px rgba(16,185,129,0.15)' },
  red:    { bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.25)',  text: 'text-red-400',     glow: '0 0 20px rgba(239,68,68,0.15)' },
  blue:   { bg: 'rgba(59,130,246,0.08)', border: 'rgba(59,130,246,0.25)', text: 'text-blue-400',    glow: '0 0 20px rgba(59,130,246,0.15)' },
  purple: { bg: 'rgba(168,85,247,0.08)', border: 'rgba(168,85,247,0.25)', text: 'text-purple-400',  glow: '0 0 20px rgba(168,85,247,0.15)' },
  cyan:   { bg: 'rgba(6,182,212,0.08)',  border: 'rgba(6,182,212,0.25)',  text: 'text-cyan-400',    glow: '0 0 20px rgba(6,182,212,0.15)' }
};

function MetricCard({ label, value, unit, icon, color = 'blue', trend }) {
  const c = COLORS[color] || COLORS.blue;

  return (
    <div
      className="metric-card"
      style={{ background: c.bg, borderColor: c.border, boxShadow: c.glow }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-wider font-bold muted">{label}</span>
        {icon && <span className={`text-sm ${c.text}`} aria-hidden="true">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className={`text-2xl font-extrabold ${c.text} font-mono`}>{value}</span>
        {unit && <span className="text-xs muted font-medium">{unit}</span>}
      </div>
      {trend !== undefined && (
        <span className={`text-[10px] font-semibold ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? '▲' : '▼'} {Math.abs(trend)}%
        </span>
      )}
    </div>
  );
}

export default function MetricsBar({ metrics = {} }) {
  const slaMet = Boolean(metrics.sla_met);

  return (
    <div className="flex gap-3 flex-wrap" role="group" aria-label="Key metrics">
      <MetricCard label="Avg wait" value={metrics.avg_wait || '—'} unit="s" color={slaMet ? 'green' : 'red'} icon="⏱" />
      <MetricCard label="Max wait" value={metrics.max_wait || '—'} unit="s" color="amber" icon="⚡" />
      <MetricCard label="Completed" value={metrics.completed || 0} color="green" icon="✓" />
      <MetricCard label="Active" value={metrics.active_passengers || 0} color="blue" icon="👥" />
      <MetricCard label="Rejections" value={metrics.rejections || 0} color="red" icon="✗" />
      <MetricCard label="Distance" value={metrics.distance || 0} unit="fl" color="purple" icon="↕" />
      <MetricCard label="Re-opts" value={metrics.reopts || 0} color="cyan" icon="↻" />
      <MetricCard
        label="SLA"
        value={slaMet ? 'Met' : 'Missed'}
        color={slaMet ? 'green' : 'red'}
        icon={slaMet ? '🟢' : '🔴'}
      />
    </div>
  );
}

export { MetricCard };
