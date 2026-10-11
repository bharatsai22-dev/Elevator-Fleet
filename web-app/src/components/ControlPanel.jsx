import React from 'react';

/**
 * Simulation control panel — Start/Pause/Reset, Speed, Strategy, Scenario.
 */
export default function ControlPanel({
  running,
  speed,
  strategy,
  scenario,
  mode,
  strategies = [],
  scenarios = [],
  onStart,
  onPause,
  onReset,
  onSpeedChange,
  onConfigure,
  onSetMode,
  simTime,
  step,
  totalSteps,
}) {
  const progressPct = totalSteps > 0 ? Math.min((step / totalSteps) * 100, 100) : 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Status bar */}
      <div className="flex items-center gap-3">
        <span className={`status-dot ${running ? 'online' : 'offline'}`} />
        <span className="text-xs font-bold uppercase tracking-wider" style={{ color: running ? 'var(--green-primary)' : 'var(--text-muted)' }}>
          {running ? 'SIMULATING' : 'PAUSED'}
        </span>
        {simTime && <span className="text-xs font-mono text-gray-500 ml-auto">{simTime}</span>}
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 rounded-sm overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
        <div
          className="h-full rounded-sm transition-all duration-300"
          style={{
            width: `${progressPct}%`,
            background: 'linear-gradient(90deg, var(--accent-primary), var(--green-primary))',
            boxShadow: '0 0 8px var(--accent-glow)',
          }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-gray-600 font-mono">
        <span>Step {step}</span>
        <span>{totalSteps}</span>
      </div>

      {/* Mode toggle */}
      <div className="flex bg-black/20 p-1 rounded-md border border-white/5">
        <button
          type="button"
          className={`flex-1 text-xs py-1.5 rounded font-bold uppercase tracking-wider transition-colors ${
            mode === 'auto' || !mode ? 'bg-[var(--accent-primary)] text-white shadow-sm' : 'text-gray-400 hover:text-white'
          }`}
          onClick={() => onSetMode && onSetMode('auto')}
        >
          Auto Traffic
        </button>
        <button
          type="button"
          className={`flex-1 text-xs py-1.5 rounded font-bold uppercase tracking-wider transition-colors ${
            mode === 'manual' ? 'bg-[var(--accent-primary)] text-white shadow-sm' : 'text-gray-400 hover:text-white'
          }`}
          onClick={() => onSetMode && onSetMode('manual')}
        >
          Manual Traffic
        </button>
      </div>

      {/* Playback controls */}
      <div className="flex gap-2">
        {!running ? (
          <button onClick={onStart} className="btn-primary flex-1 justify-center">
            ▶ Start
          </button>
        ) : (
          <button onClick={onPause} className="btn-ghost flex-1 justify-center" style={{ borderColor: 'var(--accent-primary)', color: 'var(--accent-primary)' }}>
            ⏸ Pause
          </button>
        )}
        <button onClick={onReset} className="btn-ghost flex-1 justify-center">
          ↻ Reset
        </button>
      </div>

      {/* Speed slider */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-[10px] uppercase tracking-wider font-bold text-gray-500">Speed</label>
          <span className="text-xs font-mono font-bold text-accent-primary">{speed}×</span>
        </div>
        <input
          type="range"
          min="0.25"
          max="20"
          step="0.25"
          value={speed}
          onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
        />
      </div>

      {/* Strategy selector */}
      <div>
        <label className="block text-[10px] uppercase tracking-wider font-bold text-gray-500 mb-1">Dispatch Strategy</label>
        <select
          value={strategy}
          onChange={(e) => onConfigure({ strategy: e.target.value })}
          className="w-full"
        >
          {strategies.map((s) => (
            <option key={s} value={s}>
              {s.toUpperCase()}{s === 'gbfs' ? ' (A* + GBFS)' : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Scenario selector */}
      <div>
        <label className="block text-[10px] uppercase tracking-wider font-bold text-gray-500 mb-1">Traffic Scenario</label>
        <select
          value={scenario}
          onChange={(e) => onConfigure({ scenario: e.target.value })}
          className="w-full"
        >
          {scenarios.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
