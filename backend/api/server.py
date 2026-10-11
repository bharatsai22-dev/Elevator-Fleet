"""
FastAPI + WebSocket Server for the Elevator Fleet Dashboard.

Endpoints:
    GET  /                  → serves the frontend
    GET  /api/config        → current simulation config
    GET  /api/strategies    → available dispatch strategies
    GET  /api/scenarios     → available traffic scenarios
    POST /api/configure     → update simulation settings
    WS   /ws                → real-time simulation state stream

The WebSocket streams JSON frames ~10× per second containing:
    - elevator positions, directions, loads, queues
    - floor call queues
    - live metrics (avg wait, max wait, SLA, completed, distance)
    - recent dispatch decisions
    - simulation clock info
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import numpy as np

# Resolve project root
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.simulator.models import Building, Elevator, Passenger
from backend.dispatch.base import DispatchStrategy
from backend.dispatch.gbfs import GBFSDispatcher
from backend.dispatch.astar import AStarSequencer
from backend.dispatch import get_strategy, get_strategy_names
from backend.scenarios.traffic import TrafficGenerator, get_scenario_names
from backend.ml.weights import DynamicWeightAdjuster
from backend.ml.predictor import TrafficPredictor
from backend.analytics.metrics import MetricsCollector


# ═══════════════════════════════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════════════════════════════
app = FastAPI(title="Elevator Fleet Dashboard")

# CORS — allow Vite dev server and any local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
_frontend_dir = os.path.join(_project_root, "frontend")
_webapp_dist = os.path.join(_project_root, "web-app", "dist")
if os.path.isdir(_webapp_dist):
    _frontend_dir = _webapp_dist
if os.path.isdir(_frontend_dir):
    app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")


# ═══════════════════════════════════════════════════════════════════════════
# Simulation state (module-level singleton)
# ═══════════════════════════════════════════════════════════════════════════
class SimState:
    """Holds the live simulation state for WebSocket streaming."""

    def __init__(self) -> None:
        self.config = self._load_config()
        self.reset()

    def _load_config(self) -> dict:
        config_path = os.path.join(_project_root, "config.json")
        with open(config_path, encoding="utf-8") as fh:
            return json.load(fh)

    def reset(
        self,
        strategy_name: str = "gbfs",
        scenario_name: str = "random_uniform",
        seed: int = 42,
        speed: float = 1.0,
    ) -> None:
        self.strategy_name = strategy_name
        self.scenario_name = scenario_name
        self.seed = seed
        self.speed = speed  # multiplier: 1.0 = real-time, 5.0 = 5x fast

        rng = np.random.default_rng(seed)

        num_floors = self.config["simulation"]["building_floors"]
        num_elevators = self.config["elevators"]["count"]
        self.building = Building.create(num_floors, num_elevators)

        self.dispatcher = get_strategy(strategy_name, self.building)
        self.sequencer = AStarSequencer(
            self.building,
            seconds_per_floor=self.config["elevators"].get(
                "seconds_per_floor", 2.0
            ),
        )

        if isinstance(self.dispatcher, GBFSDispatcher):
            self.weight_adjuster = DynamicWeightAdjuster(
                self.dispatcher,
                self.building,
                sla_wait_target_sec=self.config["tuning"]["sla_wait_target_sec"],
                adjustment_interval_sec=self.config["tuning"][
                    "weight_update_interval_sec"
                ],
                load_variance_threshold=self.config["tuning"][
                    "load_variance_threshold"
                ],
            )
            self.dispatcher.sla_target_sec = self.config["tuning"][
                "sla_wait_target_sec"
            ]
        else:
            self.weight_adjuster = None

        self.predictor = TrafficPredictor(self.building)
        self.traffic = TrafficGenerator(
            self.building, self.config, rng, scenario_name=scenario_name
        )
        self.rng = rng
        self.metrics = MetricsCollector()

        self.step: int = 0
        self.sim_time: datetime = datetime.now()
        self.time_per_step: float = self.config["simulation"]["time_per_step_sec"]
        self.total_steps: int = self.config["simulation"]["duration_steps"]

        self.running: bool = False
        self.mode: str = getattr(self, "mode", "auto")
        self.active_passengers: dict[str, dict] = {}
        self.recent_decisions: list[dict] = []

    # ------------------------------------------------------------------
    # Side-by-side comparison state
    # ------------------------------------------------------------------
    def reset_comparison(
        self,
        strategy_a: str,
        strategy_b: str,
        scenario_name: str,
        seed: int,
    ) -> None:
        """Set up two parallel simulations for comparison mode."""
        self.comparison_mode = True
        self.comparison_a = _create_mini_sim(
            self.config, strategy_a, scenario_name, seed
        )
        self.comparison_b = _create_mini_sim(
            self.config, strategy_b, scenario_name, seed
        )


sim = SimState()


# ═══════════════════════════════════════════════════════════════════════════
# Mini simulation helper for comparison mode
# ═══════════════════════════════════════════════════════════════════════════
def _create_mini_sim(
    config: dict, strategy_name: str, scenario_name: str, seed: int
) -> dict:
    """Create a minimal simulation state dict."""
    rng = np.random.default_rng(seed)
    num_floors = config["simulation"]["building_floors"]
    num_elevators = config["elevators"]["count"]
    building = Building.create(num_floors, num_elevators)
    dispatcher = get_strategy(strategy_name, building)
    traffic = TrafficGenerator(building, config, rng, scenario_name=scenario_name)
    metrics = MetricsCollector()
    sequencer = AStarSequencer(building)

    return {
        "building": building,
        "dispatcher": dispatcher,
        "traffic": traffic,
        "metrics": metrics,
        "sequencer": sequencer,
        "rng": rng,
        "active_passengers": {},
        "strategy_name": strategy_name,
        "step": 0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# One simulation step
# ═══════════════════════════════════════════════════════════════════════════
def _run_step(s: SimState) -> None:
    """Execute one step of the simulation."""
    s.step += 1
    s.sim_time += timedelta(seconds=s.time_per_step)

    # 1. Generate calls
    if getattr(s, "mode", "auto") == "auto":
        calls = s.traffic.generate_calls(s.sim_time, s.time_per_step)
    else:
        calls = []
    for _, _, priority, _ in calls:
        s.metrics.record_call(priority)

    # 2. Dispatch
    for call_data in calls:
        floor, direction, priority, dest = call_data
        call_id = s.building.add_call(floor, direction, priority)

        passenger = Passenger(
            passenger_id=call_id,
            origin_floor=floor,
            dest_floor=dest,
            priority=priority,
            direction=direction,
            request_time=s.sim_time,
            weight_kg=float(np.clip(s.rng.normal(75, 15), 40, 120)),
        )

        if isinstance(s.dispatcher, GBFSDispatcher):
            s.dispatcher.register_pending_call(call_id, s.sim_time.timestamp())

        eid, est_wait, decision = s.dispatcher.assign_elevator(
            floor, direction, priority
        )
        elevator = s.building.elevators[eid]

        if priority == "EXPRESS":
            elevator.add_express_call(floor)
        else:
            elevator.add_to_queue(floor, direction)

        s.active_passengers[call_id] = {
            "passenger": passenger,
            "elevator_id": eid,
            "direction": direction,
            "state": "WAITING",
            "reopt_count": 0,
        }

        s.predictor.observe_call(floor, s.sim_time)

        # Keep last 30 decisions for dashboard
        s.recent_decisions.append({
            "step": s.step,
            "floor": floor,
            "direction": direction,
            "priority": priority,
            "dest": dest,
            "elevator": eid,
            "score": round(decision.get("best_score", 0), 2),
            "wait_est": round(est_wait, 1),
        })
        if len(s.recent_decisions) > 30:
            s.recent_decisions = s.recent_decisions[-30:]

    # 3. Move elevators
    for elevator in s.building.elevators:
        if not elevator.is_operational:
            continue
        target = _next_target(elevator)
        if target is not None:
            elevator.move_one_floor(target)
            s.metrics.record_distance()
            if elevator.current_floor == target:
                _handle_arrival(s, elevator, target)
        else:
            elevator.set_idle()
            elevator.idle_time_sec += s.time_per_step

    # 4. A* reopt (every 10 steps)
    if s.step % 10 == 0:
        for elev in s.building.elevators:
            if elev.has_pending_stops():
                result = s.sequencer.optimize_route(elev)
                if result["reopt_triggered"] and result["reopt_accepted"]:
                    s.metrics.record_reopt()

    # 5. Weight adjustment (every 30 steps)
    if s.step % 30 == 0 and s.step > 0 and s.weight_adjuster:
        s.weight_adjuster.adjust_weights(force=True)

    # 6. Prediction (every 60 steps)
    if s.step % 60 == 0 and s.step > 0:
        s.predictor.update_prediction()


def _next_target(elevator: Elevator) -> int | None:
    """Determine the next floor target."""
    if elevator.express_queue:
        return min(elevator.express_queue, key=lambda f: abs(f - elevator.current_floor))

    passenger_dests = [p.dest_floor for p in elevator.passengers]
    
    # If the elevator is full, it must ignore pickups and focus ONLY on dropoffs
    if len(elevator.passengers) >= elevator.max_passengers:
        above = sorted(f for f in passenger_dests if f >= elevator.current_floor)
        below = sorted(
            (f for f in passenger_dests if f <= elevator.current_floor),
            reverse=True,
        )
    else:
        # We can respect the target_sequence if we have capacity
        if hasattr(elevator, "target_sequence") and elevator.target_sequence:
            return elevator.target_sequence[0]
            
        above = sorted(f for f in elevator.up_queue + passenger_dests if f >= elevator.current_floor)
        below = sorted(
            (f for f in elevator.down_queue + passenger_dests if f <= elevator.current_floor),
            reverse=True,
        )

    if elevator.direction == "UP":
        return above[0] if above else (below[0] if below else None)
    elif elevator.direction == "DOWN":
        return below[0] if below else (above[0] if above else None)
    else:
        a = above[0] if above else None
        b = below[0] if below else None
        if a is not None and b is not None:
            return a if abs(a - elevator.current_floor) <= abs(b - elevator.current_floor) else b
        return a if a is not None else b


def _handle_arrival(s: SimState, elevator: Elevator, floor: int) -> None:
    """Handle boarding/alighting at a floor."""
    # Alight
    alighting = [p for p in elevator.passengers if p.dest_floor == floor]
    for pax in alighting:
        pax.dropoff_time = s.sim_time
        elevator.alight_passenger(pax)
        s.building.record_completion(pax)
        wait = pax.waiting_time_sec() or 0.0
        s.metrics.record_completion(wait)
        if isinstance(s.dispatcher, GBFSDispatcher):
            s.dispatcher.complete_call(pax.passenger_id)
        s.active_passengers.pop(pax.passenger_id, None)

    # Board
    boarding_ids = [
        cid for cid, rec in s.active_passengers.items()
        if rec["state"] == "WAITING"
        and rec["elevator_id"] == elevator.elevator_id
        and rec["passenger"].origin_floor == floor
    ]
    for cid in boarding_ids:
        rec = s.active_passengers[cid]
        pax = rec["passenger"]
        if elevator.board_passenger(pax):
            pax.pickup_time = s.sim_time
            rec["state"] = "ONBOARD"
            s.building.remove_call(pax.origin_floor, pax.direction, pax.priority)
        else:
            s.metrics.record_rejection()

    # Clean queues
    still_waiting = any(
        r["state"] == "WAITING" and r["passenger"].origin_floor == floor
        for r in s.active_passengers.values()
    )
    if not still_waiting:
        if floor in elevator.up_queue:
            elevator.up_queue.remove(floor)
        if floor in elevator.down_queue:
            elevator.down_queue.remove(floor)
        if floor in elevator.express_queue:
            elevator.express_queue.remove(floor)
            
    if hasattr(elevator, "target_sequence") and floor in elevator.target_sequence:
        elevator.target_sequence.remove(floor)


# ═══════════════════════════════════════════════════════════════════════════
# State snapshot for WebSocket
# ═══════════════════════════════════════════════════════════════════════════
def _build_snapshot(s: SimState) -> dict:
    """Build a JSON-serialisable snapshot of the current simulation state."""
    elevators = []
    for e in s.building.elevators:
        elevators.append({
            "id": e.elevator_id,
            "floor": e.current_floor,
            "direction": e.direction,
            "passengers": len(e.passengers),
            "max_passengers": e.max_passengers,
            "load_kg": round(e.total_load_kg, 1),
            "max_load_kg": e.max_load_kg,
            "load_pct": round(e.occupancy_percent(), 1),
            "up_queue": list(e.up_queue),
            "down_queue": list(e.down_queue),
            "express_queue": list(e.express_queue),
            "operational": e.is_operational,
            "trips": e.trips_completed,
            "distance": e.total_distance_floors,
        })

    # Floor waiting counts
    floors = {}
    for i in range(1, s.building.num_floors + 1):
        waiting_up = sum(1 for f, _ in s.building.up_calls if f == i)
        waiting_down = sum(1 for f, _ in s.building.down_calls if f == i)
        waiting_express = sum(1 for f, _ in s.building.express_calls if f == i)
        floors[str(i)] = {
            "up": waiting_up,
            "down": waiting_down,
            "express": waiting_express,
        }

    return {
        "step": s.step,
        "total_steps": s.total_steps,
        "sim_time": s.sim_time.strftime("%H:%M:%S"),
        "running": s.running,
        "strategy": s.strategy_name,
        "scenario": s.scenario_name,
        "mode": getattr(s, "mode", "auto"),
        "speed": s.speed,
        "num_floors": s.building.num_floors,
        "elevators": elevators,
        "floors": floors,
        "metrics": {
            "total_calls": s.metrics.total_calls,
            "completed": s.metrics.total_completed,
            "avg_wait": round(s.metrics.avg_wait_time, 1),
            "max_wait": round(s.metrics.max_wait_time, 1),
            "sla_target": s.config["tuning"]["sla_wait_target_sec"],
            "sla_met": s.metrics.avg_wait_time <= s.config["tuning"]["sla_wait_target_sec"],
            "distance": s.metrics.total_distance,
            "rejections": s.metrics.capacity_rejections,
            "reopts": s.metrics.reopt_count,
            "emergency": s.metrics.emergency_calls,
            "active_passengers": len(s.active_passengers),
        },
        "decisions": s.recent_decisions[-15:],
        "weights": (
            s.dispatcher.get_current_weights()
            if isinstance(s.dispatcher, GBFSDispatcher)
            else {}
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# REST Endpoints
# ═══════════════════════════════════════════════════════════════════════════
@app.get("/")
async def root():
    """Serve the dashboard frontend."""
    index_path = os.path.join(_frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Frontend not found. Place index.html in frontend/</h1>")


@app.get("/api/config")
async def get_config():
    return sim.config


@app.get("/api/strategies")
async def get_strategies():
    return {"strategies": get_strategy_names()}


@app.get("/api/scenarios")
async def get_scenarios():
    return {"scenarios": get_scenario_names()}


class ConfigureRequest(BaseModel):
    strategy: str = "gbfs"
    scenario: str = "random_uniform"
    seed: int = 42
    speed: float = 1.0


@app.post("/api/configure")
async def configure(req: ConfigureRequest):
    sim.reset(
        strategy_name=req.strategy,
        scenario_name=req.scenario,
        seed=req.seed,
        speed=req.speed,
    )
    return {"status": "ok", "config": {
        "strategy": req.strategy,
        "scenario": req.scenario,
        "seed": req.seed,
        "speed": req.speed,
    }}


@app.post("/api/start")
async def start():
    sim.running = True
    return {"status": "running"}


@app.post("/api/pause")
async def pause():
    sim.running = False
    return {"status": "paused"}


@app.post("/api/reset")
async def reset():
    sim.reset(
        strategy_name=sim.strategy_name,
        scenario_name=sim.scenario_name,
        seed=sim.seed,
        speed=sim.speed,
    )
    return {"status": "reset"}


@app.post("/api/speed")
async def set_speed(speed: float = 1.0):
    sim.speed = max(0.1, min(50.0, speed))
    return {"speed": sim.speed}


class ManualCallRequest(BaseModel):
    from_floor: int = 1
    to_floor: int = 8
    count: int = 1
    elevator_id: int | None = None


class ElevatorToggleRequest(BaseModel):
    elevator_id: int


@app.post("/api/toggle_elevator")
async def toggle_elevator(req: ElevatorToggleRequest):
    if 0 <= req.elevator_id < len(sim.building.elevators):
        elevator = sim.building.elevators[req.elevator_id]
        elevator.is_operational = not elevator.is_operational
        if not elevator.is_operational:
            elevator.direction = "IDLE"
        return {"status": "success", "operational": elevator.is_operational}
    return {"status": "error"}


@app.post("/api/manual_call")
async def manual_call(req: ManualCallRequest):
    """Inject a manual passenger call into the simulation."""
    direction = "UP" if req.to_floor > req.from_floor else "DOWN"
    for _ in range(req.count):
        call_id = sim.building.add_call(req.from_floor, direction, "NORMAL")
        passenger = Passenger(
            passenger_id=call_id,
            origin_floor=req.from_floor,
            dest_floor=req.to_floor,
            priority="NORMAL",
            direction=direction,
            request_time=sim.sim_time,
            weight_kg=75.0,
        )
        if isinstance(sim.dispatcher, GBFSDispatcher):
            sim.dispatcher.register_pending_call(call_id, sim.sim_time.timestamp())
        if req.elevator_id is not None and 0 <= req.elevator_id < len(sim.building.elevators):
            eid = req.elevator_id
            est_wait = 0.0
            decision = {"best_score": 999.0}
        else:
            eid, est_wait, decision = sim.dispatcher.assign_elevator(
                req.from_floor, direction, "NORMAL"
            )
        elevator = sim.building.elevators[eid]
        elevator.add_to_queue(req.from_floor, direction)
        
        sim.active_passengers[call_id] = {
            "passenger": passenger,
            "elevator_id": eid,
            "direction": direction,
            "state": "WAITING",
            "reopt_count": 0,
        }
        sim.recent_decisions.append({
            "step": sim.step,
            "floor": req.from_floor,
            "direction": direction,
            "priority": "NORMAL",
            "dest": req.to_floor,
            "elevator": eid,
            "score": round(decision.get("best_score", 0), 2),
            "wait_est": round(est_wait, 1),
        })
    return {"status": "ok", "calls_added": req.count}


class SimModeRequest(BaseModel):
    mode: str = "manual"  # "auto" or "manual"


@app.post("/api/sim/mode")
async def set_sim_mode(req: SimModeRequest):
    """Toggle simulation auto/manual mode."""
    sim.mode = req.mode
    return {"status": "ok", "mode": req.mode}


# ═══════════════════════════════════════════════════════════════════════════
# WebSocket — real-time state streaming
# ═══════════════════════════════════════════════════════════════════════════
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            if sim.running and sim.step < sim.total_steps:
                # Run multiple steps per frame at higher speeds
                steps_per_frame = max(1, int(sim.speed))
                for _ in range(steps_per_frame):
                    if sim.step < sim.total_steps:
                        _run_step(sim)

            # Send state snapshot
            snapshot = _build_snapshot(sim)
            await ws.send_json(snapshot)

            # Frame rate: ~10 FPS base, adjusted by speed
            delay = max(0.03, 0.1 / max(sim.speed, 0.5))
            await asyncio.sleep(delay)

    except WebSocketDisconnect:
        pass
    except Exception:
        await ws.close()


# ═══════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  ELEVATOR FLEET DASHBOARD")
    print("  Open http://localhost:8000 in your browser")
    print("=" * 60)
    uvicorn.run(
        "backend.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
