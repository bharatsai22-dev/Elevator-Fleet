import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

import Dashboard from './pages/Dashboard';
import Fleet from './pages/Fleet';
import AStarEngine from './pages/AStarEngine';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import AlertCenter from './pages/AlertCenter';
import Arena from './pages/Arena';
import TeamUp from './pages/TeamUp';
import History from './pages/History';
import Profile from './pages/Profile';
import XAIGuide from './components/XAIGuide';
import Sidebar from './components/Sidebar';

// Works on localhost and when the app is opened from another machine.
const HOST = window.location.hostname || 'localhost';
const API_BASE = `http://${HOST}:8000`;
const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${HOST}:8000/ws`;

const RETRY_MIN_MS = 1000;
const RETRY_MAX_MS = 10000;

function App() {
  const [simState, setSimState] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [strategies, setStrategies] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const retryRef = useRef(RETRY_MIN_MS);

  // Fetch initial metadata
  useEffect(() => {
    const load = (path, key, setter) =>
      fetch(`${API_BASE}${path}`)
        .then((r) => {
          if (!r.ok) throw new Error(`${path} returned ${r.status}`);
          return r.json();
        })
        .then((d) => setter(d[key] || []))
        .catch((err) => console.error(`Could not load ${path}:`, err));

    load('/api/strategies', 'strategies', setStrategies);
    load('/api/scenarios', 'scenarios', setScenarios);
  }, []);

  // WebSocket connection with automatic reconnect
  useEffect(() => {
    let ws;
    let timer;
    let closedByUs = false;

    const connect = () => {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        retryRef.current = RETRY_MIN_MS;
        setIsConnected(true);
      };
      ws.onmessage = (event) => {
        try {
          setSimState(JSON.parse(event.data));
        } catch (err) {
          console.error('WS parse error', err);
        }
      };
      ws.onclose = () => {
        setIsConnected(false);
        if (closedByUs) return;
        timer = setTimeout(connect, retryRef.current);
        retryRef.current = Math.min(retryRef.current * 2, RETRY_MAX_MS);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closedByUs = true;
      clearTimeout(timer);
      if (ws) ws.close();
    };
  }, []);

  const apiCall = useCallback(async (endpoint, payload = null) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload ? JSON.stringify(payload) : null
      });
      if (!res.ok) console.error(`${endpoint} failed with status ${res.status}`);
    } catch (err) {
      console.error(`Error calling ${endpoint}:`, err);
    }
  }, []);

  const handleStart = () => apiCall('/api/start');
  const handlePause = () => apiCall('/api/pause');
  const handleReset = () => apiCall('/api/reset');
  const handleSpeedChange = (speed) => apiCall(`/api/speed?speed=${encodeURIComponent(speed)}`);
  const handleConfigure = (config) => apiCall('/api/configure', config);
  const handleManualCall = (from_floor, to_floor, count) =>
    apiCall('/api/manual_call', { from_floor, to_floor, count });
  const handleToggleElevator = (elevator_id) =>
    apiCall('/api/toggle_elevator', { elevator_id });
  const handleSetMode = (mode) => apiCall('/api/sim/mode', { mode });

  const decisions = simState?.decisions;
  const latestDecision = decisions && decisions.length > 0 ? decisions[decisions.length - 1] : null;

  return (
    <Router>
      <div
        className="flex h-screen w-full overflow-hidden"
        style={{ background: 'var(--bg-primary)', color: 'var(--text)' }}
      >
        <Sidebar isConnected={isConnected} />

        <main
          className="flex-1 flex flex-col min-w-0 overflow-hidden relative"
          style={{ background: 'var(--bg-primary)' }}
        >
          <Routes>
            <Route
              path="/"
              element={
                <Dashboard
                  simState={simState}
                  strategies={strategies}
                  scenarios={scenarios}
                  onStart={handleStart}
                  onPause={handlePause}
                  onReset={handleReset}
                  onSpeedChange={handleSpeedChange}
                  onConfigure={handleConfigure}
                  onManualCall={handleManualCall}
                  onToggleElevator={handleToggleElevator}
                  onSetMode={handleSetMode}
                />
              }
            />
            <Route path="/fleet" element={<Fleet simState={simState} />} />
            <Route path="/astar" element={<AStarEngine simState={simState} />} />
            <Route path="/analytics" element={<Analytics simState={simState} />} />
            <Route path="/alerts" element={<AlertCenter />} />
            <Route path="/arena" element={<Arena />} />
            <Route path="/history" element={<History />} />
            <Route path="/team" element={<TeamUp />} />
            <Route path="/profile" element={<Profile />} />
            <Route
              path="/settings"
              element={
                <Settings
                  simState={simState}
                  strategies={strategies}
                  scenarios={scenarios}
                  onConfigure={handleConfigure}
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <XAIGuide decision={latestDecision} />
      </div>
    </Router>
  );
}

export default App;
