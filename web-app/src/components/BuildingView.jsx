import React, { useMemo } from 'react';
import { Plus, Power } from 'lucide-react';

/**
 * Building visualization: realistic technical schematic of elevator shafts with floor indicators.
 *
 * Props:
 *   elevators: array from the WebSocket snapshot
 *   numFloors: total floors in the building
 *   floors:    waiting queues, { "1": { up: 2, down: 0, express: 0 }, ... }
 *   onManualCall: function to spawn a call from a floor
 *   onToggleElevator: function to turn an elevator on/off
 */
export default function BuildingView({ elevators = [], numFloors = 15, floors = {}, onManualCall, onToggleElevator }) {
  const floorNumbers = useMemo(
    () => Array.from({ length: numFloors }, (_, i) => numFloors - i),
    [numFloors]
  );

  const rowHeight = `${100 / numFloors}%`;

  const dirArrow = (dir) => (dir === 'UP' ? '▲' : dir === 'DOWN' ? '▼' : '●');
  const dirColor = (dir) =>
    dir === 'UP' ? 'var(--success)' : dir === 'DOWN' ? 'var(--critical)' : 'var(--muted)';

  const handlePlusClick = (f) => {
    if (onManualCall) {
      // Default behavior: go to lobby from upper floors, or go to top floor from lobby
      const dest = f === 1 ? numFloors : 1;
      onManualCall(f, dest, 1);
    }
  };

  return (
    <div className="flex gap-1 select-none h-full w-full p-3" style={{ minHeight: 0 }}>
      {/* Floor labels with + button */}
      <div className="flex flex-col pr-2 pt-6 pb-6" style={{ minWidth: '48px' }}>
        {floorNumbers.map((f) => (
          <div key={f} className="flex items-center justify-end gap-2 text-xs num muted group relative" style={{ height: rowHeight }}>
            <button 
              onClick={() => handlePlusClick(f)}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded transition-opacity bg-[var(--surface-2)] hover:bg-[var(--primary)] hover:text-white border border-[var(--border)]"
              title={`Call elevator from floor ${f}`}
            >
              <Plus size={12} strokeWidth={3} />
            </button>
            <span>{f}</span>
          </div>
        ))}
      </div>

      {/* Shafts */}
      <div className="flex gap-3 flex-1 min-w-0">
        {elevators.map((elev) => {
          const bottomPct = ((elev.floor - 1) / Math.max(numFloors - 1, 1)) * 100;
          const carHeight = Math.max(100 / numFloors - 1, 4);
          const label = `Elevator ${elev.id + 1}, floor ${elev.floor}, ${elev.passengers} of ${elev.max_passengers} passengers${
            elev.operational ? '' : ', offline'
          }`;

          return (
            <div
              key={elev.id}
              className="flex flex-col items-center flex-1"
              style={{ minWidth: '56px', maxWidth: '90px' }}
              role="img"
              aria-label={label}
            >
              <div className="text-xs font-bold mb-1 tracking-wider h-5" style={{ color: 'var(--primary)' }}>
                E{elev.id + 1}
              </div>

              {/* The Shaft */}
              <div
                className="relative w-full flex-1 overflow-hidden"
                style={{
                  backgroundColor: '#050914', // Deep dark shaft
                  border: '1px solid var(--border)',
                  boxShadow: 'inset 0 0 10px rgba(0,0,0,0.8)'
                }}
              >
                {/* Technical schematic details: Guide rails */}
                <div className="absolute left-[15%] top-0 bottom-0 w-px bg-white/5" />
                <div className="absolute right-[15%] top-0 bottom-0 w-px bg-white/5" />

                {/* Floor grid lines */}
                {floorNumbers.map((f) => (
                  <div
                    key={f}
                    className="absolute w-full flex items-center justify-between px-1"
                    style={{
                      top: `${((numFloors - f) / numFloors) * 100}%`,
                      height: '1px',
                    }}
                  >
                     <div className="w-full h-px bg-white/10" />
                  </div>
                ))}

                {/* Waiting counts (Call buttons on floors) */}
                {floorNumbers.map((f) => {
                  const d = floors[String(f)];
                  const waiting = d ? (d.up || 0) + (d.down || 0) + (d.express || 0) : 0;
                  if (waiting === 0) return null;
                  return (
                    <div
                      key={`w-${f}`}
                      className="absolute right-1 text-[9px] font-bold z-10"
                      style={{
                        top: `${((numFloors - f + 0.5) / numFloors) * 100}%`,
                        transform: 'translateY(-50%)',
                        color: 'var(--accent)',
                        background: 'rgba(0,0,0,0.5)',
                        padding: '1px 3px',
                        borderRadius: '2px',
                        border: '1px solid var(--border)'
                      }}
                    >
                      {waiting}
                    </div>
                  );
                })}

                {/* Hoist Cable */}
                <div 
                  className="absolute left-1/2 top-0 w-0.5 bg-gray-600/50 -translate-x-1/2 transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
                  style={{ bottom: `${bottomPct}%` }}
                />

                {/* Counterweight (moves opposite to car) */}
                <div 
                  className="absolute right-[5%] w-1 bg-gray-700/40 border border-gray-600/50 transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
                  style={{ 
                    top: `${bottomPct}%`, 
                    height: '20px' 
                  }}
                />

                {/* Car */}
                <div
                  className="absolute left-[10%] right-[10%] flex flex-col transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] z-20"
                  style={{
                    bottom: `${bottomPct * (1 - carHeight / 100)}%`,
                    height: `${carHeight}%`,
                    minHeight: '24px',
                  }}
                >
                  {/* Car Roof / Engine mechanism */}
                  <div className="h-1.5 w-full bg-gray-800 border-x border-t border-gray-600 flex justify-center items-end">
                     <div className="w-2 h-1 bg-gray-500 rounded-t-sm" />
                  </div>
                  
                  {/* Car Cabin - Technical schematic look */}
                  <div className="flex-1 w-full flex relative overflow-hidden shadow-[0_0_15px_rgba(59,130,246,0.15)]" 
                       style={{ 
                         background: elev.operational ? 'var(--surface-2)' : 'rgba(127,29,29,0.5)',
                         border: `1px solid ${elev.operational ? 'var(--primary)' : 'var(--critical)'}`
                       }}>
                    
                    {/* Sliding Doors Split */}
                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/20 -translate-x-1/2" />
                    
                    {/* Passenger count badge */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-[9px] font-extrabold num px-1 rounded-sm shadow-sm" style={{ 
                        background: elev.operational ? 'rgba(59,130,246,0.15)' : 'rgba(239,68,68,0.2)',
                        color: elev.operational ? 'var(--text)' : '#fca5a5',
                        border: `1px solid ${elev.operational ? 'rgba(59,130,246,0.4)' : 'rgba(239,68,68,0.5)'}`
                      }}>
                        {elev.passengers}/{elev.max_passengers}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Status footer */}
              <div className="mt-1 flex items-center gap-1 h-5 w-full group">
                <span className="text-sm font-bold" style={{ color: dirColor(elev.direction) }} aria-hidden="true">
                  {dirArrow(elev.direction)}
                </span>
                <span className="text-xs num font-bold flex-1">F{elev.floor}</span>
                <button
                  onClick={() => onToggleElevator && onToggleElevator(elev.id)}
                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded transition-opacity"
                  title={elev.operational ? "Turn off elevator" : "Turn on elevator"}
                  style={{ color: elev.operational ? 'var(--critical)' : 'var(--success)' }}
                >
                  <Power size={12} strokeWidth={3} />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Waiting summary */}
      <div className="flex flex-col pl-2 pt-6 pb-6" style={{ minWidth: '40px' }} aria-hidden="true">
        {floorNumbers.map((f) => {
          const d = floors[String(f)];
          const up = d?.up || 0;
          const down = d?.down || 0;
          return (
            <div key={f} className="flex items-center gap-1 text-[9px] num" style={{ height: rowHeight }}>
              {up > 0 && <span style={{ color: 'var(--success)' }}>↑{up}</span>}
              {down > 0 && <span style={{ color: 'var(--critical)' }}>↓{down}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
