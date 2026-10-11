# Elevator Fleet Dispatcher — Project Work Log & Future Roadmap

**Repository:** [bharatsai22-dev/Elevator-Fleet](https://github.com/bharatsai22-dev/Elevator-Fleet)  
**Project Title:** Heuristic Elevator Fleet Dispatcher Using A* State-Space Search & Explainable AI  
**Last Updated:** October 2026  

---

## 📌 Executive Summary

The **Elevator Fleet Dispatcher** project transforms traditional, inefficient first-come-first-served (FCFS) elevator dispatching into an intelligent, heuristic-driven state-space optimization system. By leveraging **A\* search**, **Greedy Best-First Search (GBFS)**, dynamic weight adjustment, machine learning traffic prediction, and modern web visualization, the platform minimizes passenger wait times, optimizes energy/travel distance, and guarantees starvation prevention during heavy rush hours.

---

## 🏆 Part 1: Previous Work Done (Completed Milestones)

### 1. Phase 1 — Architecture & Core Modularization
- **Modular Codebase Separation**: Transitioned from a monolithic script into cleanly decoupled packages:
  - `backend/simulator/` & `backend/engine/`: Core simulation loop, physics/clock models, and elevator state machines.
  - `backend/dispatch/`: Algorithmic dispatch strategies (`astar.py`, `gbfs.py`, `nearest.py`, `round_robin.py`, `scan.py`).
  - `backend/scenarios/`: Deterministic synthetic traffic generators.
  - `backend/analytics/`: Performance metrics, telemetry logging, and SLA monitoring.
  - `backend/ml/`: Predictive traffic models and dynamic weight adaptation.
- **Configuration-Driven System**: All simulation parameters (floors, elevator count, speeds, door open durations, SLA thresholds) isolated in `config.json`.
- **Reproducibility**: Seeded random number generator (RNG) engine for repeatable and scientifically verifiable experiments.

### 2. Phase 2 — Algorithmic Intelligence & Heuristics
- **Enhanced Greedy Best-First Search (GBFS)**:
  - Multi-term scoring function incorporating:
    1. `distance`: Absolute distance between elevator and call floor.
    2. `direction_bias`: Priority given to elevators already moving toward the destination.
    3. `load_balance`: Penalty for heavily loaded elevators.
    4. `wait_time`: Exponential urgency weighting for passengers waiting the longest.
    5. `fairness`: Anti-starvation term preventing isolated floor neglect.
    6. `emergency_bonus`: Priority handling for critical and VIP requests.
- **A\* State-Space Search Engine**:
  - Evaluation function $f(n) = g(n) + h(n)$, balancing accumulated movement cost $g(n)$ with an admissible heuristic $h(n)$.
  - Time-based cost metrics (`seconds_per_floor`, door delay penalties).
  - Search safeguards: 50,000-node expansion limits and large-queue fallbacks.
  - Enforced hard physical capacity constraints (elevators reject new boarders when at max capacity).
- **Proactive Idle Parking**:
  - Predicts upcoming passenger concentrations (e.g., ground floor during morning rush) and automatically repositions idle cars.

### 3. Phase 3 — Baseline Strategies & Realistic Traffic Scenarios
- **Four Standardized Traffic Scenarios**:
  - **Morning Rush**: Heavy inbound traffic (~80% UP traffic starting from ground floor, $\lambda=4.0$).
  - **Lunch Peak**: Heavy inter-floor and cafeteria traffic (~50/50 bidirectionally, $\lambda=3.0$).
  - **Evening Rush**: Heavy outbound traffic (~80% DOWN traffic heading to ground floor, $\lambda=3.5$).
  - **Random Uniform**: Baseline standard distribution across all floors ($\lambda=2.0$).
- **Three Industry Baseline Dispatchers**:
  - `NearestLiftDispatcher`: Industry-standard greedy nearest-car assignment.
  - `RoundRobinDispatcher`: Cyclic distributor for basic load balancing.
  - `SCANDispatcher`: Traditional elevator-algorithm (sweep up, sweep down).
- **Strategy Registry**: Factory pattern (`get_strategy()`) enabling runtime swapping of dispatch algorithms.

### 4. Phase 4 — Benchmarking Suite & Scientific Analytics
- **Automated Benchmark Runner (`benchmark.py`)**:
  - Runs full matrix: $\text{Strategies} \times \text{Scenarios} \times N\text{ Seeds}$.
  - Evaluates Key Performance Indicators (KPIs):
    - Average & 95th-percentile Wait Time ($s$)
    - Average Travel Time ($s$)
    - SLA Violations Percentage ($>60s$ waiting threshold)
    - Total Car Travel Distance (floors traversed)
    - Passenger Throughput & Car Utilization
  - Generates auto-formatted results: `results/benchmark_results.csv` and `results/benchmark_summary.md`.

### 5. Phase 5 — Modern Enterprise Web Application (`web-app/`)
- **Modern React + Vite Frontend**: Replaced legacy HTML/JS with a reactive, component-driven SPA:
  - `Dashboard.jsx`: Live control center showing active elevators, shaft animations, live KPIs, and passenger queues.
  - `Fleet.jsx`: Detailed elevator telemetry, load status, maintenance state, and manual overrides.
  - `AStarEngine.jsx`: Interactive state-space exploration visualizer showing open list, closed list, and $f(n) = g(n) + h(n)$ cost computations.
  - `Arena.jsx`: Side-by-side head-to-head comparison engine running A*/GBFS against baseline algorithms under identical passenger traffic.
  - `AlertCenter.jsx`: Real-time safety events, capacity warnings, and operational telemetry notifications.
  - `Analytics.jsx`: Historical response charts, wait-time distributions, and heatmaps.
  - `History.jsx`, `Settings.jsx`, `TeamUp.jsx`, `Profile.jsx`: Comprehensive admin and user management tools.
- **FastAPI Backend & WebSocket Streaming**:
  - High-frequency (~10 FPS) bidirectional WebSocket connection streaming simulation frames directly to the frontend.
  - REST endpoints for creating passenger calls, toggling scenarios, and adjusting speed.

### 6. Phase 6 — Enterprise Features, Explainable AI (XAI) & Edge Cases
- **Explainable AI (`backend/xai/explainer.py`)**:
  - Generates human-readable rationales explaining *why* a specific elevator was chosen (e.g., *"Elevator 2 chosen over Elevator 1 because Elevator 1 is near max capacity and Elevator 2 is already en-route down"*).
- **Edge Cases & Emergency Modes**:
  - **Fire Recall Mode**: Instantly recalls all cars to the ground floor, opens doors, and halts new passenger dispatches.
  - **VIP Express Mode**: Direct point-to-point dispatch bypassing intermediate stops.
  - **Out-of-Service / Breakdown Handling**: Dynamically redistributes stranded passenger requests to active cars.
- **Database & User Roles (`backend/database.py`, `backend/auth.py`)**:
  - SQLite backend (`users`, `history`) providing Role-Based Access Control (Admin, Operator, Viewer).

---

## 🔮 Part 2: Upcoming Work To Be Done (Roadmap)

### 📌 Milestone 1: Test Suite & API Alignment (Immediate Priority)
- [ ] **Synchronize Test Suite**:
  - Update `tests/test_simulator.py` to match the enhanced `backend/engine/` structures, new telemetry constructor signatures, and updated weight dictionary keys.
  - Ensure all 58+ unit tests pass cleanly via automated CI.
- [ ] **Unified Engine Interface**:
  - Consolidate legacy `backend/simulator/` references with the unified `backend/engine/` architecture.

### 📌 Milestone 2: Advanced AI & Optimization Models (Next Sprint)
- [ ] **Deep Reinforcement Learning (DRL) Dispatcher**:
  - Implement a Deep Q-Network (DQN) or Proximal Policy Optimization (PPO) agent as an additional benchmark strategy against A* and GBFS.
  - Train policies against peak-hour scenarios to learn proactive anticipatory elevator parking.
- [ ] **Dynamic Passenger Boarding Model**:
  - Add realistic passenger loading/unloading delays dependent on elevator crowd density (e.g., $1.2s$ per passenger entering/exiting, with congestion penalties at $>80\%$ capacity).
- [ ] **Energy Consumption Heuristic**:
  - Expand $g(n)$ cost function to incorporate motor energy models (kwh consumption during acceleration, deceleration, and idle holding).

### 📌 Milestone 3: Reporting & Data Exports
- [ ] **PDF & CSV Export Engine**:
  - Enable one-click export of benchmarking runs and simulation history logs into polished academic PDF reports and CSV spreadsheets.
- [ ] **Simulation Replay Feature**:
  - Record complete simulation sessions into time-stamped JSON trace files with scrubbable rewind/fast-forward playback in the web dashboard.

### 📌 Milestone 4: Hardware & IoT Integration
- [ ] **MQTT / Modbus IoT Bridge**:
  - Develop a lightweight virtual IoT bridge that maps simulation commands to standard building automation protocols (BACnet / Modbus / MQTT) for physical elevator hardware compatibility.
- [ ] **Floor Calling Physical Kiosk UI**:
  - Create a lightweight touch-friendly tablet kiosk interface for wall-mounted elevator hall call stations.

### 📌 Milestone 5: DevOps, Containerization & Cloud Deployment
- [ ] **Docker & Docker Compose**:
  - Build multi-stage Dockerfiles:
    - Container 1: Python FastAPI backend (`uvicorn backend.api.server:app`).
    - Container 2: Nginx serving production-built React static files (`web-app/dist`).
  - Provide a single `docker-compose up` command for instant local or cloud deployment.
- [ ] **GitHub Actions CI/CD Pipeline**:
  - Automated workflow on push:
    - Linting with Flake8 / Oxlint.
    - Automated unit tests & benchmark validation.
    - Automated build of React web-app.
- [ ] **Cloud Live Demo**:
  - Deploy public live demo instance on Render / Railway / Fly.io with WebSocket proxying.

---

## 📊 Summary Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                   VITE + REACT 19 WEB APPLICATION                      │
│   Dashboard  │  Fleet  │  Arena (VS)  │  A* Engine  │  Alerts  │ XAI   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / WebSockets (10 FPS)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                               │
│            REST Endpoints  │  WebSocket Stream  │  Auth/RBAC           │
└──────────────┬────────────────────┬────────────────────┬───────────────┘
               │                    │                    │
               ▼                    ▼                    ▼
     ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
     │  DISPATCH ENGINE │  │  ELEVATOR FLEET  │  │ XAI & ALERTS │
     │  • A* Search     │  │  • Multi-Car Sim │  │ • Reasoning  │
     │  • GBFS (6 Terms)│  │  • Traffic Gens  │  │ • Safety Ops │
     │  • Baselines     │  │  • Floor Queues  │  │ • DB History │
     └──────────────────┘  └──────────────────┘  └──────────────┘
```

---

*Authored for the Elevator Fleet Project repository at https://github.com/bharatsai22-dev/Elevator-Fleet.*
