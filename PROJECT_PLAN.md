# Project Plan: Elevator-Fleet

## Goal
Show that your smart dispatcher (GBFS + A*) beats simple methods, and present it with a great live dashboard.

## Final Structure
```
Elevator-Fleet/
├── backend/
│   ├── simulator/      (building, lifts, passengers, clock)
│   ├── dispatch/       (your GBFS+A*, nearest, round-robin, SCAN)
│   ├── scenarios/      (morning rush, lunch, evening, random)
│   ├── analytics/      (metrics, telemetry CSV, charts)
│   ├── ml/             (traffic predictor, weight tuning)
│   └── api/            (FastAPI + WebSocket)
├── frontend/           (web dashboard)
├── tests/
├── results/            (CSV, charts, benchmark table)
├── config.json
└── README.md
```

## Phase 1: Clean the Core
- Split code into clear modules (simulator, dispatch, metrics).
- Move all settings to `config.json`.
- Make the simulation run **without** any UI (needed for benchmarks).
- Add a seed so every run can be repeated.

## Phase 2: Improve the Algorithm
- Add direction-aware scoring.
- Add the waiting-time (fairness) term.
- Keep the hard capacity limit.
- Use the traffic predictor to park idle lifts.
- Make sure the A* heuristic never overestimates.

## Phase 3: Scenarios and Baselines
- Build the 4 traffic scenarios.
- Build 3 baselines: nearest-lift, round-robin, SCAN.
- Same traffic goes to every method for a fair test.

## Phase 4: Benchmark and Results
- Metrics: average wait, max wait, SLA violations %, floors travelled, lift utilization.
- Run each method on each scenario with many seeds (e.g., 20).
- Save a results table and charts (bar chart, wait-time distribution).
- Tune weights with grid search, then compare with the RandomForest idea.

## Phase 5: Web Dashboard
- **Backend:** FastAPI streams simulation state through WebSocket.
- **Screen layout:**
  - Center: building with sliding lifts and floor queues
  - Top: live stats (average wait, SLA, served)
  - Right: decision log ("Lift 2 chosen, score 34")
  - Bottom: live charts
  - Controls: start/pause, speed, scenario, strategy
- **Wow feature:** side-by-side mode, your method vs a baseline on the same traffic.
- Dark theme, smooth animations, color-coded load, floor heatmap toggle.

## Phase 6: Quality
- Tests for capacity limit, scoring, and scenario repeatability.
- Edge cases: lift out of service, VIP/fire mode.
- Basic error handling and input checks.

## Phase 7: Documentation and Submission
- README with architecture diagram, demo GIF, run steps, results table.
- Report: problem, method, heuristic explained, experiments, results, limits, future work.
- Demo script: a 3-minute flow for your professor.
- Presentation slides.

## Suggested Time Split
| Phase | Share of time |
|---|---|
| 1. Core cleanup | 10% |
| 2. Algorithm | 15% |
| 3. Scenarios + baselines | 15% |
| 4. Benchmarks | 15% |
| 5. Dashboard | 25% |
| 6. Quality | 5% |
| 7. Docs + demo | 15% |
