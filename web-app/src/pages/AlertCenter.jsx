import React from 'react';
import { ShieldAlert, Bell, CheckCircle } from 'lucide-react';

export default function AlertCenter({ alerts = [] }) {
  // Mock alerts if none provided from backend yet
  const displayAlerts = alerts.length > 0 ? alerts : [
    { id: 1, type: 'WARNING', msg: 'SLA breached on Floor 4 (>45s wait)', time: '10:42 AM', ack: false },
    { id: 2, type: 'CRITICAL', msg: 'Elevator 2 offline (Maintenance)', time: '10:35 AM', ack: true },
    { id: 3, type: 'INFO', msg: 'Scenario "Morning Rush" started', time: '10:00 AM', ack: true },
  ];

  const getIcon = (type) => {
    if (type === 'CRITICAL') return <ShieldAlert size={20} className="text-red-500" />;
    if (type === 'WARNING') return <Bell size={20} className="text-amber-500" />;
    return <CheckCircle size={20} className="text-blue-500" />;
  };

  return (
    <div className="flex-1 p-8 flex flex-col h-full overflow-y-auto custom-scrollbar gap-6">
      <div className="flex justify-between items-end border-b border-glass-border pb-4">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight mb-2">Alert Center</h2>
          <p className="text-secondary text-sm">System faults, SLA breaches, and operational warnings.</p>
        </div>
        <button className="btn-ghost">Acknowledge All</button>
      </div>

      <div className="flex flex-col gap-3">
        {displayAlerts.map(alert => (
          <div key={alert.id} className={`glass-panel p-4 flex items-center justify-between ${!alert.ack ? 'border-l-4 border-l-red-500' : 'opacity-70'}`}>
            <div className="flex items-center gap-4">
              <div className={`p-2 rounded-sm ${
                alert.type === 'CRITICAL' ? 'bg-red-500/20' : 
                alert.type === 'WARNING' ? 'bg-amber-500/20' : 'bg-blue-500/20'
              }`}>
                {getIcon(alert.type)}
              </div>
              <div>
                <div className="text-sm font-bold text-white">{alert.msg}</div>
                <div className="text-xs text-gray-500">{alert.time}</div>
              </div>
            </div>
            {!alert.ack && (
              <button className="text-xs bg-bg-secondary border border-glass-border hover:border-accent-primary px-3 py-1.5 rounded transition-colors">
                Acknowledge
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
