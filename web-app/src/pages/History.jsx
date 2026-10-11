import React from 'react';
import { History as HistoryIcon, Download } from 'lucide-react';

export default function History() {
  return (
    <div className="flex-1 p-8 flex flex-col h-full overflow-y-auto custom-scrollbar gap-6">
      <div className="flex justify-between items-end border-b border-glass-border pb-4">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight mb-2">Simulation History</h2>
          <p className="text-secondary text-sm">Review past runs and generate PDF reports (Phase 5).</p>
        </div>
        <button className="btn-primary">
          <Download size={16} /> Export PDF Report
        </button>
      </div>

      <div className="glass-panel overflow-hidden">
        <table className="w-full text-left text-sm text-gray-300">
          <thead className="bg-bg-tertiary border-b border-glass-border">
            <tr>
              <th className="p-4 font-bold uppercase tracking-wider text-[10px] text-gray-500">Date</th>
              <th className="p-4 font-bold uppercase tracking-wider text-[10px] text-gray-500">Scenario</th>
              <th className="p-4 font-bold uppercase tracking-wider text-[10px] text-gray-500">Strategy</th>
              <th className="p-4 font-bold uppercase tracking-wider text-[10px] text-gray-500">Avg Wait</th>
              <th className="p-4 font-bold uppercase tracking-wider text-[10px] text-gray-500">SLA %</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-glass-border">
            <tr className="hover:bg-white/5 transition-colors">
              <td className="p-4 font-mono text-xs">2026-10-09 18:30</td>
              <td className="p-4">Morning Rush</td>
              <td className="p-4">GBFS + A*</td>
              <td className="p-4 font-mono text-green-400">12.4s</td>
              <td className="p-4 font-mono">98%</td>
            </tr>
            <tr className="hover:bg-white/5 transition-colors">
              <td className="p-4 font-mono text-xs">2026-10-08 14:15</td>
              <td className="p-4">Random Uniform</td>
              <td className="p-4">Nearest Lift</td>
              <td className="p-4 font-mono text-red-400">45.2s</td>
              <td className="p-4 font-mono">75%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
