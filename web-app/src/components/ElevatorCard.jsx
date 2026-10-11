import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

const len = (a) => (Array.isArray(a) ? a.length : 0);

export default function ElevatorCard({ elevator }) {
  const { operational, direction } = elevator;

  const status = !operational
    ? { text: 'Out of service', cls: 'badge-critical' }
    : direction === 'UP'
    ? { text: 'Moving up', cls: 'badge-warning' }
    : direction === 'DOWN'
    ? { text: 'Moving down', cls: 'badge-warning' }
    : { text: 'Idle', cls: 'badge-success' };

  const DirIcon = direction === 'UP' ? ArrowUp : direction === 'DOWN' ? ArrowDown : Minus;
  const dirColor =
    direction === 'UP' ? 'var(--success)' : direction === 'DOWN' ? 'var(--critical)' : 'var(--muted)';

  const load = Math.min(100, Math.max(0, elevator.load_pct || 0));
  const loadColor = load > 85 ? 'var(--critical)' : load > 50 ? 'var(--primary)' : 'var(--success)';

  const up = len(elevator.up_queue);
  const down = len(elevator.down_queue);
  const express = len(elevator.express_queue);
  const queued = up + down + express;

  return (
    <article className="panel panel-pad gap-4 elevator-card" aria-label={`Elevator ${elevator.id + 1}`}>
      <div className="flex justify-between items-center pb-3 gap-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-xl num"
            style={{
              background: operational ? 'var(--surface-2)' : 'rgba(239,68,68,0.15)',
              color: operational ? 'var(--primary)' : 'var(--critical)',
              border: `1px solid ${operational ? 'var(--border)' : 'var(--critical)'}`
            }}
          >
            E{elevator.id + 1}
          </div>
          <div>
            <div className="stat-label !mb-0">Current floor</div>
            <div className="text-2xl font-bold flex items-center gap-2">
              <span className="num">{elevator.floor}</span>
              <span style={{ color: dirColor }} aria-hidden="true"><DirIcon size={16} /></span>
            </div>
          </div>
        </div>
        <span className={`badge ${status.cls}`}>{status.text}</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="inset rounded p-3">
          <div className="stat-label">Load</div>
          <div className="flex items-end justify-between">
            <span className="text-lg font-bold num">{load}%</span>
            <span className="text-xs muted">{elevator.passengers}/{elevator.max_passengers} pax</span>
          </div>
          <div className="progress mt-2" role="progressbar" aria-valuenow={load} aria-valuemin={0} aria-valuemax={100} aria-label="Car load">
            <span style={{ width: `${load}%`, background: loadColor, transition: 'width .3s ease' }} />
          </div>
        </div>

        <div className="inset rounded p-3">
          <div className="stat-label">Queue</div>
          <div className="flex items-end justify-between">
            <span className="text-lg font-bold num">{queued}</span>
            <span className="text-xs muted">{queued === 1 ? 'stop' : 'stops'}</span>
          </div>
          <div className="mt-2 flex gap-1 h-1" aria-label={`${up} up, ${down} down, ${express} express`}>
            <div className="h-full rounded-sm" style={{ flex: up || 0.1, background: 'var(--success)' }} />
            <div className="h-full rounded-sm" style={{ flex: down || 0.1, background: 'var(--critical)' }} />
            <div className="h-full rounded-sm" style={{ flex: express || 0.1, background: 'var(--primary)' }} />
          </div>
          <div className="flex gap-3 mt-2 text-[10px] muted">
            <span>Up {up}</span><span>Down {down}</span><span>Express {express}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
        <div>
          <div className="stat-label">Total trips</div>
          <div className="text-sm font-bold num">{elevator.trips}</div>
        </div>
        <div>
          <div className="stat-label">Distance</div>
          <div className="text-sm font-bold num">{elevator.distance} floors</div>
        </div>
      </div>
    </article>
  );
}
