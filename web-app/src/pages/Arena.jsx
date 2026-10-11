import React from 'react';
import { Swords, Trophy } from 'lucide-react';

export default function Arena() {
  return (
    <div className="flex-1 p-8 flex flex-col h-full overflow-y-auto custom-scrollbar gap-6">
      <div className="flex items-center gap-4 border-b border-glass-border pb-4">
        <div className="w-14 h-14 bg-purple-500/20 rounded-sm flex items-center justify-center border border-purple-500/50">
          <Swords size={28} className="text-purple-400" />
        </div>
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">The Arena</h2>
          <p className="text-secondary text-sm">Run side-by-side benchmarking battles between dispatch algorithms.</p>
        </div>
      </div>

      <div className="glass-panel p-6 flex flex-col gap-6">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold text-white uppercase tracking-widest">Setup Battle</h3>
          <button className="btn-primary">START BENCHMARK</button>
        </div>
        
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-bg-secondary p-4 rounded-sm border border-glass-border">
            <div className="text-sm font-bold text-accent-primary mb-2">Algorithm A</div>
            <select className="w-full bg-bg-primary p-2 rounded">
              <option>GBFS + A* (Enhanced)</option>
              <option>Round Robin</option>
            </select>
          </div>
          <div className="bg-bg-secondary p-4 rounded-sm border border-glass-border">
            <div className="text-sm font-bold text-blue-400 mb-2">Algorithm B</div>
            <select className="w-full bg-bg-primary p-2 rounded">
              <option>Nearest Lift (Legacy)</option>
              <option>SCAN</option>
            </select>
          </div>
        </div>

        <div className="bg-bg-tertiary p-10 rounded-sm border border-glass-border border-dashed flex flex-col items-center justify-center text-gray-500 gap-4 mt-4">
          <Trophy size={48} className="text-gray-600" />
          <p>Run a battle to see metrics comparison (Wait Time, Distance, SLA %)</p>
        </div>
      </div>
    </div>
  );
}
