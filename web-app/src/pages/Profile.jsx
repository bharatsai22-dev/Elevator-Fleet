import React from 'react';
import { User, LogOut } from 'lucide-react';

export default function Profile() {
  return (
    <div className="flex-1 p-8 flex flex-col h-full overflow-y-auto custom-scrollbar gap-6">
      <div className="border-b border-glass-border pb-4">
        <h2 className="text-3xl font-bold text-white tracking-tight mb-2">My Profile</h2>
        <p className="text-secondary text-sm">Manage your account and theme preferences.</p>
      </div>

      <div className="glass-panel p-6 max-w-xl">
        <div className="flex items-center gap-6 mb-8">
          <div className="w-24 h-24 rounded-sm bg-bg-tertiary flex items-center justify-center border-2 border-accent-primary ">
            <User size={40} className="text-accent-primary" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-white">Bharat Sai</h3>
            <p className="text-gray-400 font-mono text-sm">Owner</p>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Theme Preference</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" name="theme" defaultChecked className="text-accent-primary" /> Midnight Console (Dark)
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" name="theme" disabled /> Light Mode (Coming Soon)
              </label>
            </div>
          </div>
          
          <div className="pt-6 border-t border-glass-border">
            <button className="btn-ghost text-red-400 hover:border-red-500 hover:bg-red-500/10">
              <LogOut size={16} /> Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
