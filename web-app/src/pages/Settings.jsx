import React, { useState } from 'react';
import { Dices, Settings as SettingsIcon } from 'lucide-react';
import PageHeader from '../components/PageHeader';

const prettify = (s) => s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

const STRATEGY_INFO = {
  gbfs: {
    name: 'GBFS dispatcher',
    desc: 'Heuristic scoring with A* route sequencing and dynamic weights.',
    recommended: true
  },
  nearest: {
    name: 'Nearest car',
    desc: 'First-come, first-served: the closest available car takes the call.'
  },
  scan: {
    name: 'SCAN sweep',
    desc: 'Each car sweeps up and down the building like a disk read head.'
  }
};

const strategyInfo = (id) =>
  STRATEGY_INFO[id] || { name: prettify(id), desc: 'Simple turn-based distribution.' };

export default function Settings({ simState, strategies, scenarios, onConfigure }) {
  const initial = {
    strategy: simState?.strategy || 'gbfs',
    scenario: simState?.scenario || 'random_uniform',
    seed: simState?.seed ?? 42
  };
  const [localConfig, setLocalConfig] = useState(initial);
  const [applied, setApplied] = useState(false);

  if (!simState) {
    return (
      <div className="flex-1 flex items-center justify-center" role="status">
        <p className="muted text-sm">Connecting…</p>
      </div>
    );
  }

  const current = {
    strategy: simState.strategy,
    scenario: simState.scenario,
    seed: simState.seed ?? 42
  };
  const isDirty =
    localConfig.strategy !== current.strategy ||
    localConfig.scenario !== current.scenario ||
    localConfig.seed !== current.seed;

  const update = (patch) => {
    setApplied(false);
    setLocalConfig((prev) => ({ ...prev, ...patch }));
  };

  const handleApply = () => {
    onConfigure(localConfig);
    setApplied(true);
  };

  const handleDiscard = () => {
    setApplied(false);
    setLocalConfig(current);
  };

  const randomizeSeed = () => update({ seed: Math.floor(Math.random() * 100000) });

  return (
    <div className="page custom-scrollbar">
      <PageHeader
        icon={SettingsIcon}
        title="System settings"
        description="Choose the dispatch algorithm and traffic profile. Applying changes restarts the simulation."
      />

      <div className="grid grid-cols-1 max-w-3xl gap-6 mt-6">
        <fieldset className="panel panel-pad border-0">
          <legend className="panel-title">Dispatch algorithm</legend>
          <div className="flex flex-col gap-3">
            {strategies.map((s) => {
              const info = strategyInfo(s);
              return (
                <label key={s} className="option" data-selected={localConfig.strategy === s}>
                  <input
                    type="radio"
                    name="strategy"
                    value={s}
                    checked={localConfig.strategy === s}
                    onChange={(e) => update({ strategy: e.target.value })}
                  />
                  <div>
                    <div className="option-title">
                      {info.name}
                      {info.recommended && <span className="badge badge-info ml-2">Recommended</span>}
                    </div>
                    <div className="option-desc">{info.desc}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </fieldset>

        <fieldset className="panel panel-pad border-0">
          <legend className="panel-title">Traffic profile</legend>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {scenarios.map((s) => (
              <label key={s} className="option" data-selected={localConfig.scenario === s}>
                <input
                  type="radio"
                  name="scenario"
                  value={s}
                  checked={localConfig.scenario === s}
                  onChange={(e) => update({ scenario: e.target.value })}
                />
                <span className="option-title">{prettify(s)}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <section className="panel panel-pad">
          <h3 className="panel-title">Random seed</h3>
          <label className="field-label" htmlFor="sim-seed">
            The same seed always produces the same traffic, so runs can be compared fairly.
          </label>
          <div className="flex gap-2 max-w-xs mt-2">
            <input
              id="sim-seed"
              type="number"
              min={0}
              className="input flex-1"
              value={localConfig.seed}
              onChange={(e) => update({ seed: Math.max(0, parseInt(e.target.value, 10) || 0) })}
            />
            <button type="button" className="btn shrink-0" onClick={randomizeSeed}>
              <Dices size={16} aria-hidden="true" /> Randomize
            </button>
          </div>
        </section>

        <div className="flex items-center gap-3 pb-10">
          <button type="button" className="btn-primary" onClick={handleApply} disabled={!isDirty}>
            Apply and restart
          </button>
          <button type="button" className="btn" onClick={handleDiscard} disabled={!isDirty}>
            Discard changes
          </button>
          <div aria-live="polite">
            {isDirty && <span className="muted text-sm">You have unapplied changes.</span>}
            {applied && !isDirty && <span className="notice notice-ok p-2">Settings applied. Simulation restarted.</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
