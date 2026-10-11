import React from 'react';

const fmtScore = (s) => (typeof s === 'number' ? s.toFixed(2) : s);

export default function DecisionLog({ decisions = [] }) {
  // Newest first
  const sorted = [...decisions].reverse();

  return (
    <section className="panel h-full" aria-label="Dispatch decision log">
      <div
        className="px-4 py-3 flex justify-between items-center shrink-0"
        style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--border)' }}
      >
        <h3 className="text-sm font-bold uppercase tracking-widest flex items-center gap-2 m-0" style={{ color: 'var(--primary)' }}>
          <span className="w-2 h-2 rounded-sm animate-pulse" style={{ background: 'var(--primary)' }} aria-hidden="true" />
          A* decision log
        </h3>
        <span className="text-xs muted num">Newest first</span>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-2 flex flex-col gap-2 custom-scrollbar" aria-live="polite">
        {sorted.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm muted p-6 text-center">
            No decisions yet. They appear here as calls are dispatched.
          </div>
        ) : (
          sorted.map((d, idx) => {
            const express = d.priority === 'EXPRESS';
            return (
              <article
                key={`${d.step}-${idx}`}
                className="log-item relative overflow-hidden rounded-lg p-3"
              >
                <div
                  className="absolute left-0 top-0 bottom-0 w-1"
                  style={{ background: express ? 'var(--critical)' : 'var(--primary)' }}
                  aria-hidden="true"
                />

                <div className="flex justify-between items-start mb-2 pl-2 gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] px-2 py-0.5 rounded num muted" style={{ background: 'var(--surface-2)' }}>
                      Step {d.step}
                    </span>
                    <span className={`badge ${express ? 'badge-critical' : 'badge-info'}`}>
                      {express ? 'Express' : 'Standard'}
                    </span>
                  </div>
                  <span className="text-xs num font-bold" style={{ color: 'var(--primary)' }}>
                    {fmtScore(d.score)} pts
                  </span>
                </div>

                <div className="pl-2 grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <div className="stat-label">Route</div>
                    <div className="font-bold flex items-center gap-1">
                      F{d.floor} <span className="muted" aria-label="to">→</span> F{d.dest}
                    </div>
                  </div>
                  <div>
                    <div className="stat-label">Assigned to</div>
                    <div className="font-bold flex items-center gap-2">
                      <span style={{ color: 'var(--accent)' }}>E{d.elevator + 1}</span>
                      <span className="text-[10px] font-normal muted">~{d.wait_est}s wait</span>
                    </div>
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
