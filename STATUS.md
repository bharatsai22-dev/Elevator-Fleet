# Project Status — Elevator Fleet Dispatcher

> **Last updated:** 2026-10-02
> **Repo:** https://github.com/bharatsai22-dev/Elevator-Fleet

---

## Completed Phases

### Phase 1: Core Cleanup ✅
- Monolithic `main.py` split into `simulator/`, `dispatch/`, `scenarios/`, `analytics/`, `ml/`
- Config-driven via `config.json`
- Seeded RNG for reproducibility
- Tests moved to `tests/`

### Phase 2: Algorithm Improvements ✅
- **GBFS enhanced** (`dispatch/gbfs.py`):
  - Positional direction awareness, en-route bonus, queue-depth penalty
  - Starvation-based fairness weight with exponential urgency
  - 6 scoring terms: direction_bias, load_balance, distance, wait_time, emergency_bonus, fairness
- **A* enhanced** (`dispatch/astar.py`):
  - Time-based cost (seconds_per_floor), node-limit safety (50k), large-queue fallback (>15 stops)
  - Formal admissibility proof in docstring
- **Idle parking** (`simulator/engine.py` → `park_idle_elevators()`):
  - Parks idle elevators at predicted high-demand floors
- **Weight adjuster** (`ml/weights.py`):
  - Added starvation rule (Rule 5) boosting fairness when max_wait > 1.5× SLA

### Phase 3: Scenarios & Baselines ✅
- **4 traffic scenarios** (`scenarios/traffic.py`):
  - `morning_rush` (80% UP from floor 1, λ=4.0)
  - `lunch_peak` (50/50, mid-floor triangular, λ=3.0)
  - `evening_rush` (80% DOWN to floor 1, λ=3.5)
  - `random_uniform` (uniform random, λ=2.0)
  - All deterministic per seed
- **3 baseline strategies** (all implement `DispatchStrategy` ABC):
  - `dispatch/nearest.py` — NearestLiftDispatcher
  - `dispatch/round_robin.py` — RoundRobinDispatcher
  - `dispatch/scan.py` — SCANDispatcher
- **Strategy registry** (`dispatch/__init__.py`):
  - `get_strategy(name, building)` factory
  - `get_strategy_names()` → ["gbfs", "nearest", "round_robin", "scan"]

### Phase 4: Benchmark & Results ✅
- **`benchmark.py`** at project root:
  - Runs strategy × scenario × N seeds matrix
  - `python benchmark.py --seeds 5` (default), `--seeds 20` (full)
  - Outputs `results/benchmark_results.csv` + `results/benchmark_summary.md`
- **54 tests passing** (`python -m unittest tests.test_simulator -v`)

---

## Next Phase: Phase 5 — Web Dashboard (25% of project)

### What to build:

**Backend** (`backend/api/`):
- FastAPI server with WebSocket streaming simulation state
- REST endpoints: start/pause, speed control, scenario/strategy selection
- The `api/__init__.py` currently exists but is empty

**Frontend** (`frontend/`):
- Directory doesn't exist yet — needs to be created
- **Screen layout per PROJECT_PLAN.md:**
  - Center: animated building with sliding elevators and floor queues
  - Top: live stats (avg wait, SLA, served count)
  - Right: decision log ("Lift 2 chosen, score 34")
  - Bottom: live charts (wait-time, utilisation over time)
  - Controls: start/pause, speed slider, scenario dropdown, strategy dropdown
- **Wow features:**
  - Side-by-side mode (GBFS vs baseline on same traffic)
  - Dark theme, smooth animations, color-coded elevator load, floor heatmap toggle

### Dependencies to add:
- `fastapi`, `uvicorn`, `websockets` (for API)
- Current `requirements.txt` has: numpy, scikit-learn, pygame, matplotlib

---

## Remaining Phases

### Phase 6: Quality
- Tests for capacity limit, scoring, scenario repeatability
- Edge cases: lift out of service, VIP/fire mode
- Error handling and input checks

### Phase 7: Documentation & Submission
- README with architecture diagram, demo GIF, run steps, results table
- Report: problem, method, heuristic, experiments, results, limits, future work
- Demo script: 3-minute flow for professor
- Presentation slides

---

## Project Structure (current)
```
advanced_elevator_dispatcher/
├── backend/
│   ├── simulator/      engine.py, models.py
│   ├── dispatch/       base.py, gbfs.py, astar.py, nearest.py, round_robin.py, scan.py
│   ├── scenarios/      traffic.py (4 scenarios)
│   ├── analytics/      metrics.py, logger.py
│   ├── ml/             predictor.py, weights.py, train.py
│   ├── api/            __init__.py (empty — Phase 5)
│   ├── main.py         CLI entry point
│   └── visualization.py  Pygame visualizer (legacy)
├── frontend/           (not yet created — Phase 5)
├── tests/              test_simulator.py (54 tests)
├── results/            benchmark_results.csv, benchmark_summary.md
├── data/               elevator_training_data.csv
├── benchmark.py        Benchmark runner
├── config.json         All settings
├── PROJECT_PLAN.md     Full 7-phase roadmap
├── STATUS.md           ← THIS FILE
└── README.md
```

## Quick Start Prompt for New Session
Copy-paste this to get started immediately:

> I'm working on an advanced elevator dispatcher project. Phases 1–4 are complete. Read `STATUS.md` and `PROJECT_PLAN.md` in the repo root for full context. Continue with **Phase 5: Web Dashboard** — FastAPI + WebSocket backend and a web frontend with live building visualization, stats panel, decision log, charts, and side-by-side comparison mode. Dark theme, smooth animations.
