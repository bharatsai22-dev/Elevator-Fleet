import React, { useEffect, useState } from 'react';
import { ArrowRight, Minus, Plus } from 'lucide-react';
import ControlPanel from '../components/ControlPanel';
import BuildingView from '../components/BuildingView';
import DecisionLog from '../components/DecisionLog';
import MetricsBar from '../components/MetricsBar';

const MAX_PASSENGERS = 6;
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const toInt = (value, fallback) => {
  const n = parseInt(value, 10);
  return Number.isNaN(n) ? fallback : n;
};

export default function Dashboard({
  simState,
  strategies,
  scenarios,
  onStart,
  onPause,
  onReset,
  onSpeedChange,
  onConfigure,
  onManualCall,
  onToggleElevator,
  onSetMode
}) {
  const [fromFloor, setFromFloor] = useState(1);
  const [toFloor, setToFloor] = useState(8);
  const [count, setCount] = useState(1);
  const [targetElev, setTargetElev] = useState('auto');
  const [notice, setNotice] = useState(null);

  // Clear the confirmation message after a few seconds
  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  if (!simState) {
    return (
      <div className="flex-1 flex items-center justify-center" role="status">
        <div className="text-center">
          <div className="spinner" />
          <p className="muted text-sm">Connecting to dispatch engine…</p>
        </div>
      </div>
    );
  }

  const topFloor = simState.num_floors;

  const handleManualCall = (e) => {
    e.preventDefault();
    if (fromFloor === toFloor) {
      setNotice({ type: 'error', text: 'Pick two different floors.' });
      return;
    }
    const targetId = targetElev === 'auto' ? undefined : parseInt(targetElev, 10);
    onManualCall(fromFloor, toFloor, count, targetId);
    setNotice({
      type: 'ok',
      text: `Call sent: floor ${fromFloor} to floor ${toFloor}, ${count} ${count === 1 ? 'passenger' : 'passengers'}.`
    });
  };

  return (
    <div className="flex-1 p-4 flex flex-col h-full overflow-hidden gap-4">
      {/* Top bar: metrics */}
      <div className="shrink-0">
        <MetricsBar
          metrics={simState.metrics}
          speed={simState.speed}
          step={simState.step}
          totalSteps={simState.total_steps}
        />
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Left column: controls and manual call */}
        <aside className="w-72 flex flex-col gap-4 overflow-y-auto custom-scrollbar shrink-0" aria-label="Simulation controls">
          <section className="panel panel-pad h-fit">
            <h3 className="panel-title">Simulation controls</h3>
            <ControlPanel
              running={simState.running}
              speed={simState.speed}
              strategy={simState.strategy}
              scenario={simState.scenario}
              mode={simState.mode}
              strategies={strategies}
              scenarios={scenarios}
              onStart={onStart}
              onPause={onPause}
              onReset={onReset}
              onSpeedChange={onSpeedChange}
              onConfigure={onConfigure}
              onSetMode={onSetMode}
              simTime={simState.sim_time}
              step={simState.step}
              totalSteps={simState.total_steps}
            />
          </section>

          <section className="panel panel-pad h-fit">
            <h3 className="panel-title justify-between">
              <span>Send a call</span>
              <span className="badge">Test tool</span>
            </h3>

            <form onSubmit={handleManualCall} className="flex flex-col gap-3">
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <label className="field-label" htmlFor="call-from">From floor</label>
                  <input
                    id="call-from"
                    type="number"
                    className="input"
                    value={fromFloor}
                    min={1}
                    max={topFloor}
                    onChange={(e) => setFromFloor(clamp(toInt(e.target.value, 1), 1, topFloor))}
                  />
                </div>
                <ArrowRight size={16} className="muted mb-3 shrink-0" aria-hidden="true" />
                <div className="flex-1">
                  <label className="field-label" htmlFor="call-to">To floor</label>
                  <input
                    id="call-to"
                    type="number"
                    className="input"
                    value={toFloor}
                    min={1}
                    max={topFloor}
                    onChange={(e) => setToFloor(clamp(toInt(e.target.value, 1), 1, topFloor))}
                  />
                </div>
              </div>

              <div>
                <span className="field-label" id="call-count-label">Passengers</span>
                <div className="stepper" role="group" aria-labelledby="call-count-label">
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => setCount((c) => clamp(c - 1, 1, MAX_PASSENGERS))}
                    disabled={count <= 1}
                    aria-label="Remove a passenger"
                  >
                    <Minus size={14} />
                  </button>
                  <span className="num" aria-live="polite">{count}</span>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => setCount((c) => clamp(c + 1, 1, MAX_PASSENGERS))}
                    disabled={count >= MAX_PASSENGERS}
                    aria-label="Add a passenger"
                  >
                    <Plus size={14} />
                  </button>
                </div>
              </div>

              <div>
                <label className="field-label" htmlFor="call-elev">Target Elevator</label>
                <select 
                  id="call-elev" 
                  className="input w-full"
                  value={targetElev}
                  onChange={(e) => setTargetElev(e.target.value)}
                >
                  <option value="auto">Auto (GBFS Dispatch)</option>
                  {simState.elevators && simState.elevators.map((e) => (
                    <option key={e.id} value={e.id}>Elevator {e.id + 1}</option>
                  ))}
                </select>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn btn-sm flex-1"
                  onClick={() => { setFromFloor(1); setToFloor(topFloor); }}
                >
                  Lobby to top
                </button>
                <button
                  type="button"
                  className="btn btn-sm flex-1"
                  onClick={() => { setFromFloor(topFloor); setToFloor(1); }}
                >
                  Top to lobby
                </button>
              </div>

              <button type="submit" className="btn-primary w-full">Send call</button>

              <div aria-live="polite">
                {notice && (
                  <p className={`notice ${notice.type === 'ok' ? 'notice-ok' : 'notice-error'}`}>{notice.text}</p>
                )}
              </div>
            </form>
          </section>
        </aside>

        {/* Center: building visualization */}
        <section className="flex-1 panel p-5 flex flex-col min-w-0" aria-label="Live building view">
          <div className="flex justify-between items-center mb-4 shrink-0 gap-4">
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold">Live operations</h3>
              <span className={`badge ${simState.running ? 'badge-success' : 'badge-warning'}`}>
                {simState.running ? 'Running' : 'Paused'}
              </span>
            </div>
            <ul className="flex gap-4 text-xs muted list-none m-0 p-0">
              <li className="flex items-center gap-2">
                <span className="legend-dot" style={{ background: 'var(--accent)' }} /> Moving
              </li>
              <li className="flex items-center gap-2">
                <span className="legend-dot" style={{ background: 'var(--muted)' }} /> Idle
              </li>
              <li className="flex items-center gap-2">
                <span className="legend-dot" style={{ background: 'var(--critical)' }} /> Offline
              </li>
            </ul>
          </div>

          <div className="viewport h-full w-full bg-[var(--surface-2)] rounded overflow-hidden relative">
            <BuildingView
              elevators={simState.elevators}
              numFloors={simState.num_floors}
              floors={simState.floors}
              onManualCall={onManualCall}
              onToggleElevator={onToggleElevator}
            />
          </div>
        </section>

        {/* Right column: decision log */}
        <aside className="w-80 flex flex-col shrink-0" aria-label="Dispatch decisions">
          <DecisionLog decisions={simState.decisions} />
        </aside>
      </div>
    </div>
  );
}
