import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  BrainCircuit,
  LineChart,
  Settings as SettingsIcon,
  ShieldAlert,
  Swords,
  History as HistoryIcon,
  Users,
  User,
  Terminal
} from 'lucide-react';

const SECTIONS = [
  {
    title: 'Dashboards',
    links: [
      { path: '/', label: 'System overview', icon: LayoutDashboard },
      { path: '/fleet', label: 'Fleet telemetry', icon: Layers },
      { path: '/astar', label: 'Routing engine', icon: BrainCircuit },
      { path: '/analytics', label: 'Performance metrics', icon: LineChart }
    ]
  },
  {
    title: 'Operations',
    links: [
      { path: '/alerts', label: 'Incident management', icon: ShieldAlert },
      { path: '/arena', label: 'Benchmark arena', icon: Swords },
      { path: '/history', label: 'Logs and reports', icon: HistoryIcon }
    ]
  },
  {
    title: 'Administration',
    links: [
      { path: '/team', label: 'Team and access', icon: Users },
      { path: '/settings', label: 'Configuration', icon: SettingsIcon }
    ]
  }
];

function Navigation() {
  return (
    <nav aria-label="Main" className="flex flex-col mt-6 flex-1 overflow-y-auto custom-scrollbar pr-2">
      {SECTIONS.map((section, i) => (
        <div key={section.title} className={i > 0 ? 'mt-4' : ''}>
          <div className="nav-heading">{section.title}</div>
          <ul className="list-none m-0 p-0 flex flex-col gap-0.5">
            {section.links.map(({ path, label, icon: Icon }) => (
              <li key={path}>
                <NavLink
                  to={path}
                  end={path === '/'}
                  className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}
                >
                  <Icon size={14} aria-hidden="true" />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export default function Sidebar({ isConnected }) {
  return (
    <aside
      className="w-60 flex flex-col p-4 shrink-0 shadow-sm z-10"
      style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)' }}
    >
      {/* Logo block */}
      <div className="flex items-center gap-3 mb-2 px-2">
        <div
          className="w-7 h-7 rounded flex items-center justify-center shadow-sm"
          style={{ background: 'var(--primary)' }}
        >
          <Terminal size={14} color="#fff" aria-hidden="true" />
        </div>
        <div className="flex flex-col">
          <span className="text-[11px] font-bold uppercase tracking-widest leading-none" style={{ color: 'var(--text)' }}>
            Elevator
          </span>
          <span className="text-[11px] font-bold uppercase tracking-widest leading-none mt-0.5" style={{ color: 'var(--primary)' }}>
            Dispatcher
          </span>
        </div>
      </div>

      <Navigation />

      {/* Bottom admin block */}
      <div className="mt-4 pt-4 px-2" style={{ borderTop: '1px solid var(--border)' }}>
        <Link to="/profile" className="profile-link flex items-center gap-3 py-2 rounded mb-2">
          <div className="profile-avatar w-7 h-7 rounded flex items-center justify-center">
            <User size={14} aria-hidden="true" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>Administrator</span>
            <span className="text-[10px] muted">Full access</span>
          </div>
        </Link>

        <div className="flex items-center gap-2 mt-4" role="status" aria-live="polite">
          <span className={`status-dot ${isConnected ? 'online' : 'offline'}`} aria-hidden="true" />
          <span className="text-[10px] font-bold uppercase tracking-widest muted">
            {isConnected ? 'Engine online' : 'Reconnecting…'}
          </span>
        </div>
      </div>
    </aside>
  );
}
