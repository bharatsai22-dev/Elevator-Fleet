import React from 'react';
import { Users, Link as LinkIcon } from 'lucide-react';

export default function TeamUp() {
  return (
    <div className="flex-1 p-8 flex flex-col h-full overflow-y-auto custom-scrollbar gap-6">
      <div className="border-b border-glass-border pb-4">
        <h2 className="text-3xl font-bold text-white tracking-tight mb-2">Team & Organization</h2>
        <p className="text-secondary text-sm">Manage roles, invites, and organization settings (Phase 9).</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6">
          <h3 className="text-lg font-bold text-white mb-4">Members</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-bg-secondary rounded border border-glass-border">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-sm bg-accent-primary flex items-center justify-center text-black font-bold">BS</div>
                <div>
                  <div className="text-sm font-bold text-white">Bharat Sai</div>
                  <div className="text-xs text-gray-500">bharat@example.com</div>
                </div>
              </div>
              <span className="badge badge-purple">OWNER</span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-bg-secondary rounded border border-glass-border">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-sm bg-gray-600 flex items-center justify-center text-white font-bold">OP</div>
                <div>
                  <div className="text-sm font-bold text-white">Operator 1</div>
                  <div className="text-xs text-gray-500">operator@example.com</div>
                </div>
              </div>
              <span className="badge badge-blue">OPERATOR</span>
            </div>
          </div>
        </div>

        <div className="glass-panel p-6 flex flex-col gap-4">
          <h3 className="text-lg font-bold text-white">Invite Links</h3>
          <p className="text-sm text-gray-400">Generate temporary links for viewers or new operators.</p>
          
          <div className="flex gap-2">
            <select className="bg-bg-secondary p-2 rounded text-sm text-white border border-glass-border">
              <option>Viewer (Read Only)</option>
              <option>Operator (Can Control)</option>
            </select>
            <button className="btn-primary flex-1">Generate Link</button>
          </div>
          
          <div className="mt-4 p-4 bg-bg-tertiary rounded-sm border border-glass-border border-dashed text-center text-sm text-gray-500">
            No active invites.
          </div>
        </div>
      </div>
    </div>
  );
}
