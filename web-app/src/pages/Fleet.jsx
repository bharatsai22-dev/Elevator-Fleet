import React, { useState } from 'react';
import { Layers } from 'lucide-react';
import ElevatorCard from '../components/ElevatorCard';
import PageHeader from '../components/PageHeader';

const statusOf = (e) => {
  if (!e.operational) return 'offline';
  return e.direction === 'IDLE' ? 'idle' : 'moving';
};

const FILTERS = [
  { id: 'all', label: 'All cars' },
  { id: 'moving', label: 'Moving' },
  { id: 'idle', label: 'Idle' },
  { id: 'offline', label: 'Offline' }
];

export default function Fleet({ simState }) {
  const [filter, setFilter] = useState('all');

  if (!simState) {
    return (
      <div className="flex-1 flex items-center justify-center" role="status">
        <p className="muted text-sm">Connecting to fleet…</p>
      </div>
    );
  }

  const { elevators } = simState;

  const totalPax = elevators.reduce((sum, e) => sum + e.passengers, 0);
  const totalCapacity = elevators.reduce((sum, e) => sum + e.max_passengers, 0);
  const utilization = totalCapacity ? Math.round((totalPax / totalCapacity) * 100) : 0;

  const counts = {
    all: elevators.length,
    moving: elevators.filter((e) => statusOf(e) === 'moving').length,
    idle: elevators.filter((e) => statusOf(e) === 'idle').length,
    offline: elevators.filter((e) => statusOf(e) === 'offline').length
  };

  const visible = filter === 'all' ? elevators : elevators.filter((e) => statusOf(e) === filter);

  return (
    <div className="page custom-scrollbar">
      <PageHeader
        icon={Layers}
        title="Fleet status"
        description="Live telemetry for every elevator car: load, queued stops, and operational health."
      >
        <div className="panel flex gap-5 p-4 items-center mt-4">
          <div className="w-40">
            <div className="stat-label">Fleet load</div>
            <div className="stat-value">
              {totalPax}<small className="text-[10px] ml-1">/{totalCapacity} pax</small>
            </div>
            <div className="progress mt-2" role="progressbar" aria-valuenow={utilization} aria-valuemin={0} aria-valuemax={100} aria-label="Fleet utilization">
              <span style={{ width: `${utilization}%` }} />
            </div>
          </div>
          <div className="stat-divider" />
          <div>
            <div className="stat-label">Moving</div>
            <div className="stat-value" style={{ color: 'var(--accent)' }}>
              {counts.moving}<small className="text-[10px] ml-1"> / {elevators.length}</small>
            </div>
          </div>
          <div className="stat-divider" />
          <div>
            <div className="stat-label">Idle</div>
            <div className="stat-value">{counts.idle}</div>
          </div>
          <div className="stat-divider" />
          <div>
            <div className="stat-label">Offline</div>
            <div className="stat-value" style={{ color: counts.offline > 0 ? 'var(--critical)' : 'var(--text)' }}>
              {counts.offline}
            </div>
          </div>
        </div>
      </PageHeader>

      <div className="tabs self-start mt-4" role="group" aria-label="Filter cars by status">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            className="tab"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
          >
            {f.label} <span className="num text-xs ml-1">({counts[f.id]})</span>
          </button>
        ))}
      </div>

      {visible.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mt-4">
          {visible.map((elev) => (
            <ElevatorCard key={elev.id} elevator={elev} />
          ))}
        </div>
      ) : (
        <div className="panel empty mt-4">No cars match this filter right now.</div>
      )}
    </div>
  );
}
