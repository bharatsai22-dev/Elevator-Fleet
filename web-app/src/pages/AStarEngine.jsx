import React from 'react';
import { BrainCircuit, Calculator, GitMerge, History } from 'lucide-react';
import WeightsPanel from '../components/WeightsPanel';
import DecisionLog from '../components/DecisionLog';
import PageHeader from '../components/PageHeader';

export default function AStarEngine({ simState }) {
  if (!simState) {
    return (
      <div className="flex-1 flex items-center justify-center" role="status">
        <p className="muted text-sm">Connecting to engine…</p>
      </div>
    );
  }

  const decisions = simState.decisions || [];
  const latest = decisions.length > 0 ? decisions[decisions.length - 1] : null;

  // Optional per-car breakdown. The backend can send:
  // latest.candidates = [{ elevator: 0, score: 12.4, wait_est: 18 }, ...]
  const candidates = latest && Array.isArray(latest.candidates) ? latest.candidates : [];
  const maxScore = candidates.reduce((m, c) => Math.max(m, Math.abs(c.score)), 0) || 1;
  const ordered = [...candidates].sort(
    (a, b) => Number(b.elevator === latest?.elevator) - Number(a.elevator === latest?.elevator)
  );

  return (
    <div className="page custom-scrollbar">
      <PageHeader
        icon={BrainCircuit}
        title="Engine inspector"
        badge={<span className="badge badge-success">Live</span>}
        description="See why the GBFS dispatcher picked a car, and how the A* sequencer orders its stops."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: weights and dynamic adjustment */}
        <div className="flex flex-col gap-6">
          <div className="h-[400px]">
            <WeightsPanel weights={simState.weights} />
          </div>

          <section className="panel panel-pad">
            <h3 className="panel-title">
              <GitMerge size={16} style={{ color: 'var(--primary)' }} aria-hidden="true" />
              Dynamic weight adjustment
            </h3>
            <p className="muted text-sm leading-relaxed mb-4">
              When waits approach the SLA target ({simState.metrics.sla_target}s), the weight adjuster shifts priority
              from distance efficiency toward fairness, so no passenger is left waiting.
            </p>
            <div className="formula">
              <div className="formula-row"><span>f(n)</span><span>g(n) + h(n)</span></div>
              <div className="formula-row"><span>g(n)</span><span>travel_cost(path)</span></div>
              <div className="formula-row"><span>h(n)</span><span>max_dist × sec/floor</span></div>
            </div>
          </section>
        </div>

        {/* Right columns: latest decision and history */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <section className="panel panel-pad">
            <h3 className="panel-title">
              <Calculator size={18} style={{ color: 'var(--primary)' }} aria-hidden="true" />
              Latest dispatch decision
            </h3>

            {latest ? (
              <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between flex-wrap gap-4 p-4 rounded-lg" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                  <div className="flex items-center gap-6">
                    <div>
                      <div className="stat-label">Request</div>
                      <div className="stat-value">
                        Floor {latest.floor} <span className="muted">to</span> {latest.dest}
                      </div>
                    </div>
                    <div className="stat-divider" />
                    <div>
                      <div className="stat-label">Priority</div>
                      <span className={`badge ${latest.priority === 'EXPRESS' ? 'badge-warning' : 'badge-info'}`}>
                        {latest.priority === 'EXPRESS' ? 'Express' : 'Standard'}
                      </span>
                    </div>
                    <div className="stat-divider" />
                    <div>
                      <div className="stat-label">Estimated wait</div>
                      <div className="stat-value">{latest.wait_est}<small>s</small></div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="stat-label">Assigned car</div>
                    <div className="stat-value" style={{ color: 'var(--accent)', fontSize: '1.75rem' }}>
                      E{latest.elevator + 1}
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-semibold mb-3">Candidate scores</h4>
                  {ordered.length > 0 ? (
                    <ul className="flex flex-col gap-3 list-none m-0 p-0">
                      {ordered.map((c) => {
                        const isWinner = c.elevator === latest.elevator;
                        return (
                          <li
                            key={c.elevator}
                            className="p-4 rounded-lg"
                            style={{
                              border: `1px solid ${isWinner ? 'var(--accent)' : 'var(--border)'}`,
                              background: 'var(--surface)'
                            }}
                          >
                            <div className="flex justify-between items-center mb-2">
                              <span className="font-semibold flex items-center gap-2">
                                E{c.elevator + 1}
                                {isWinner && <span className="badge badge-success">Selected</span>}
                              </span>
                              <span className="num font-semibold">{Number(c.score).toFixed(2)} pts</span>
                            </div>
                            <div className="bar-track">
                              <div
                                className={`bar-fill ${isWinner ? 'is-winner' : ''}`}
                                style={{ width: `${Math.max(6, (Math.abs(c.score) / maxScore) * 100)}%` }}
                              />
                            </div>
                            {c.wait_est !== undefined && (
                              <div className="muted text-xs mt-2 num">Estimated wait: {c.wait_est}s</div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <div className="notice notice-info">
                      <p>
                        Showing the selected car only. Per-car scores appear here once the backend includes a{' '}
                        <code>candidates</code> list in each decision. Selected score:{' '}
                        <strong className="num">{latest.score} pts</strong>.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="empty">No decisions yet. Send a call from the dashboard to see how it is dispatched.</div>
            )}
          </section>

          <section className="panel panel-pad flex flex-col">
            <h3 className="panel-title">
              <History size={16} style={{ color: 'var(--primary)' }} aria-hidden="true" />
              Recent decisions
            </h3>
            <div className="h-[340px] flex flex-col min-h-0">
              <DecisionLog decisions={decisions} />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
