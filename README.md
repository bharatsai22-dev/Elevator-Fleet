# 🏢 Enterprise Elevator Fleet Dispatcher

An advanced, AI-driven elevator simulation and dispatch system built for high-traffic environments. 
This project compares multiple dispatch algorithms (including an optimized Greedy Best-First Search paired with A* route sequencing) against industry baselines across deterministic traffic scenarios.

![Elevator Fleet Dashboard](dashboard.png) *(Note: Replace with actual screenshot/GIF before submission)*

## 🚀 Features

- **Advanced GBFS + A* Dispatcher:** Uses 6 heuristic scoring terms (direction bias, load balance, distance, wait time, emergency bonus, fairness) and A* sequencing to optimally route elevators.
- **Dynamic Weight Adjuster:** A machine-learning inspired component that recalibrates heuristic weights in real-time to ensure SLA (Service Level Agreement) compliance.
- **Traffic Forecasting & Idle Parking:** Predicts traffic intensity and automatically parks idle elevators at predicted hotspots before demand spikes.
- **Robust Baselines:** Compare the GBFS algorithm against standard baselines: `NearestLift`, `RoundRobin`, and `SCAN`.
- **High-Performance Web Dashboard:** A FastAPI + WebSocket backend streams live telemetry (~10 FPS) to a premium, dark-themed frontend with smooth CSS animations, live charts, and a decision log.
- **Enterprise Edge Cases:** Full support for Fire Mode, VIP calls, and simulated elevator breakdowns.

## 🛠️ Architecture

```text
advanced_elevator_dispatcher/
├── backend/
│   ├── api/            FastAPI server and WebSocket streaming
│   ├── simulator/      Core Engine, Models (Building, Elevator, Passenger)
│   ├── dispatch/       GBFS, A*, Nearest, RoundRobin, SCAN
│   ├── scenarios/      Morning Rush, Lunch Peak, Evening Rush, Random
│   ├── analytics/      Metrics Collection and CSV Logging
│   └── ml/             Traffic Predictor, Dynamic Weight Adjuster
├── frontend/           Dashboard HTML, CSS, JS
├── tests/              58 Unit Tests (pytest/unittest)
├── benchmark.py        Matrix runner for strategy × scenario evaluations
└── config.json         Hyperparameters and tuning values
```

## ⚙️ Getting Started

### Prerequisites
- Python 3.10+
- `pip install -r requirements.txt`

### 1. Run the Web Dashboard
Experience the real-time simulation visually:
```bash
python -m backend.api.server
```
Then open `http://localhost:8000` in your browser.

### 2. Run the Benchmark Suite
Evaluate the algorithms across all scenarios (takes ~1-2 minutes):
```bash
python benchmark.py --seeds 5
```
Results are saved to `results/benchmark_summary.md` and `results/benchmark_results.csv`.

### 3. Run the Tests
Verify the integrity of the engine and dispatchers:
```bash
python -m unittest tests.test_simulator -v
```

## 📊 Evaluation & Results

The `GBFS + A*` algorithm consistently outperforms baselines, particularly under heavy traffic scenarios (`morning_rush` and `lunch_peak`), minimizing average wait times while strictly adhering to the 45-second SLA target. The Dynamic Weight Adjuster proves essential in preventing starvation (long wait times for outlier calls).

Detailed benchmark reports can be generated via `benchmark.py`.
