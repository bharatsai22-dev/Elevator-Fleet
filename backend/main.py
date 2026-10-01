"""
Enterprise Elevator Fleet Simulator — Main Entry Point.

Orchestrates the full simulation loop:
    1. Generate calls (Poisson-distributed traffic)
    2. GBFS dispatches each call to the optimal elevator
    3. A* optimises each elevator's floor sequence
    4. Elevators move one floor per step
    5. Passengers board / alight
    6. Dynamic weights recalibrate every 30 steps
    7. Traffic predictor updates every 60 steps
    8. Telemetry is streamed to CSV throughout

Usage:
    python -m backend.main                 # uses config.json
    python -m backend.main config.json     # custom config
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np

# ---------------------------------------------------------------------------
# Resolve imports — works whether run as `python -m backend.main` from the
# project root **or** `python backend/main.py`
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.simulation.models import Building, Elevator, Passenger
from backend.algorithms.gbfs_dispatcher import GBFSDispatcher
from backend.algorithms.astar_sequencer import AStarSequencer
from backend.algorithms.dynamic_weights import DynamicWeightAdjuster
from backend.algorithms.prediction import TrafficPredictor
from backend.simulation.logger import TelemetryLogger


# ═══════════════════════════════════════════════════════════════════════════
# Simulator
# ═══════════════════════════════════════════════════════════════════════════
class ElevatorFleetSimulator:
    """Production-grade elevator fleet simulation engine."""

    def __init__(self, config_path: str = "config.json") -> None:
        self.config = self._load_config(config_path)

        # --- Core simulation objects ---
        num_floors = self.config["simulation"]["building_floors"]
        num_elevators = self.config["elevators"]["count"]
        self.building = Building.create(num_floors, num_elevators)

        # --- AI components ---
        self.gbfs = GBFSDispatcher(self.building)
        self.astar = AStarSequencer(self.building)
        self.weight_adjuster = DynamicWeightAdjuster(
            self.gbfs,
            self.building,
            sla_wait_target_sec=self.config["tuning"]["sla_wait_target_sec"],
            adjustment_interval_sec=self.config["tuning"][
                "weight_update_interval_sec"
            ],
            load_variance_threshold=self.config["tuning"][
                "load_variance_threshold"
            ],
        )
        self.traffic_predictor = TrafficPredictor(self.building)

        # --- Telemetry ---
        data_dir = os.path.join(_project_root, "data")
        os.makedirs(data_dir, exist_ok=True)
        csv_path = os.path.join(data_dir, "elevator_training_data.csv")
        self.logger = TelemetryLogger(csv_filename=csv_path)

        # --- Simulation clock ---
        self.total_steps: int = self.config["simulation"]["duration_steps"]
        self.time_per_step: float = self.config["simulation"]["time_per_step_sec"]
        self.current_step: int = 0
        self.sim_time: datetime = datetime.now()

        # --- Active passengers (in-flight, keyed by call_id) ---
        self._active_passengers: dict[str, dict] = {}

        # --- Counters ---
        self.metrics = {
            "total_calls": 0,
            "total_completed": 0,
            "total_wait_time": 0.0,
            "max_wait_time": 0.0,
            "total_distance": 0,
            "emergency_calls": 0,
            "capacity_rejections": 0,
            "reopt_count": 0,
        }

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------
    @staticmethod
    def _load_config(path: str) -> dict:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------
    # Traffic generation (Poisson)
    # ------------------------------------------------------------------
    def _get_lambda_multiplier(self, hour: int) -> float:
        """Return the Poisson λ multiplier for the current hour."""
        tc = self.config["traffic"]
        for mode_name, mode in tc.items():
            start = mode["start_hour"]
            end = mode["end_hour"]
            if start < end:
                if start <= hour < end:
                    return mode["lambda_multiplier"]
            else:  # wraps midnight
                if hour >= start or hour < end:
                    return mode["lambda_multiplier"]
        return 1.0  # default

    def generate_calls(self) -> list[tuple[int, str, str, int]]:
        """Generate random calls for the current step."""
        if self.config["simulation"].get("manual_mode", False):
            return []

        hour = self.sim_time.hour
        lam = 2.0 * self._get_lambda_multiplier(hour) / 60.0 * self.time_per_step
        num_calls = int(np.random.poisson(lam))

        calls: list[tuple[int, str, str, int]] = []
        max_floor = self.config["simulation"]["building_floors"]

        for _ in range(num_calls):
            floor = int(np.random.randint(1, max_floor + 1))
            dest = floor
            while dest == floor:
                dest = int(np.random.randint(1, max_floor + 1))
                
            direction = "UP" if dest > floor else "DOWN"
            priority = "EXPRESS" if np.random.random() < 0.05 else "NORMAL"
            calls.append((floor, direction, priority, dest))
            self.metrics["total_calls"] += 1
            if priority == "EXPRESS":
                self.metrics["emergency_calls"] += 1

        return calls
    # ------------------------------------------------------------------
    # Call processing (GBFS)
    # ------------------------------------------------------------------
    def process_calls(self, calls: list[tuple[int, str, str, int]] | list[tuple[int, str, str, int, int | None]]) -> None:
        """Dispatch each incoming call via GBFS or manually."""
        for call_data in calls:
            floor = call_data[0]
            direction = call_data[1]
            priority = call_data[2]
            dest = call_data[3]
            assigned_eid = call_data[4] if len(call_data) > 4 else None

            call_id = self.building.add_call(floor, direction, priority)

            passenger = Passenger(
                passenger_id=call_id,
                origin_floor=floor,
                dest_floor=dest,
                priority=priority,
                direction=direction,
                request_time=self.sim_time,
                weight_kg=float(np.clip(np.random.normal(75, 15), 40, 120)),
            )

            # GBFS or Manual assignment
            if assigned_eid is not None:
                eid = assigned_eid
                elevator = self.building.elevators[eid]
                best_score = 0.0
                weights_used = {}
            else:
                eid, est_wait, decision = self.gbfs.assign_elevator(
                    floor, direction, priority
                )
                elevator = self.building.elevators[eid]
                best_score = decision["best_score"]
                weights_used = decision["weights_used"]

            # Add to appropriate queue
            if priority == "EXPRESS":
                elevator.add_express_call(floor)
            else:
                elevator.add_to_queue(floor, direction)

            # Also queue the destination floor
            dest_dir = "UP" if dest > floor else "DOWN"
            elevator.add_to_queue(dest, dest_dir)

            # Track passenger in-flight
            self._active_passengers[call_id] = {
                "passenger": passenger,
                "elevator_id": eid,
                "direction": direction,
                "state": "WAITING",  # WAITING → ONBOARD → COMPLETED
                "reopt_count": 0,
            }

            # Telemetry
            self.traffic_predictor.observe_call(floor, self.sim_time)
            self.logger.log_call_assignment(
                call_id=call_id,
                passenger=passenger,
                elevator_id=eid,
                gbfs_score=best_score,
                weights=weights_used,
                traffic_intensity=len(self.building.get_pending_calls()),
                elevator_load_kg=elevator.total_load_kg,
            )

    # ------------------------------------------------------------------
    # Elevator movement
    # ------------------------------------------------------------------
    def move_elevators(self) -> None:
        """Advance every elevator by one floor (or idle)."""
        for elevator in self.building.elevators:
            if not elevator.is_operational:
                continue

            target = self._next_target(elevator)

            if target is not None:
                elevator.move_one_floor(target)
                self.metrics["total_distance"] += 1

                # Arrived at target?
                if elevator.current_floor == target:
                    self._handle_arrival(elevator, target)
            else:
                elevator.set_idle()
                elevator.idle_time_sec += self.time_per_step

    def _next_target(self, elevator: Elevator) -> int | None:
        """Determine the next floor the elevator should head towards."""
        # Priority: EXPRESS > direction-matching queue > other queue
        if elevator.express_queue:
            return min(
                elevator.express_queue,
                key=lambda f: abs(f - elevator.current_floor),
            )

        # Also consider destination floors of on-board passengers
        passenger_dests = [p.dest_floor for p in elevator.passengers]
        above = sorted(
            f for f in elevator.up_queue + passenger_dests
            if f >= elevator.current_floor
        )
        below = sorted(
            (f for f in elevator.down_queue + passenger_dests
             if f <= elevator.current_floor),
            reverse=True,
        )

        if elevator.direction == "UP":
            if above:
                return above[0]
            if below:
                return below[0]
        elif elevator.direction == "DOWN":
            if below:
                return below[0]
            if above:
                return above[0]
        else:  # IDLE — go whichever is actually closer
            a = above[0] if above else None
            b = below[0] if below else None
            if a is not None and b is not None:
                return (
                    a
                    if abs(a - elevator.current_floor)
                    <= abs(b - elevator.current_floor)
                    else b
                )
            return a if a is not None else b

        # If nothing in the preferred direction, serve any queue
        all_floors = elevator.all_pending_floors()
        if all_floors:
            return min(all_floors, key=lambda f: abs(f - elevator.current_floor))

        return None

    def _handle_arrival(self, elevator: Elevator, floor: int) -> None:
        """Handle passenger boarding and alighting at *floor*."""
        # --- Alight passengers whose destination is this floor ---
        alighting = [p for p in elevator.passengers if p.dest_floor == floor]
        for pax in alighting:
            pax.dropoff_time = self.sim_time
            elevator.alight_passenger(pax)
            self.building.record_completion(pax)

            # Update metrics
            wait = pax.waiting_time_sec() or 0.0
            self.metrics["total_completed"] += 1
            self.metrics["total_wait_time"] += wait
            self.metrics["max_wait_time"] = max(
                self.metrics["max_wait_time"], wait
            )

            # Telemetry completion
            rec = self._active_passengers.pop(pax.passenger_id, None)
            astar_cost = 0.0
            reopt_count = 0
            if rec:
                reopt_count = rec.get("reopt_count", 0)
            self.logger.log_call_completion(
                call_id=pax.passenger_id,
                passenger=pax,
                elevator_id=elevator.elevator_id,
                astar_cost=astar_cost,
                reopt_count=reopt_count,
                traffic_intensity=len(self.building.get_pending_calls()),
            )

        # --- Board waiting passengers at this floor ---
        boarding_ids = []
        for cid, rec in self._active_passengers.items():
            if (
                rec["state"] == "WAITING"
                and rec["elevator_id"] == elevator.elevator_id
                and rec["passenger"].origin_floor == floor
            ):
                boarding_ids.append(cid)

        rejected_ids = []
        for cid in boarding_ids:
            rec = self._active_passengers[cid]
            pax = rec["passenger"]
            if elevator.board_passenger(pax):
                pax.pickup_time = self.sim_time
                rec["state"] = "ONBOARD"
            else:
                self.metrics["capacity_rejections"] += 1
                rejected_ids.append(cid)

        # Re-dispatch rejected passengers to another elevator
        for cid in rejected_ids:
            rec = self._active_passengers[cid]
            pax = rec["passenger"]
            new_eid, _, _ = self.gbfs.assign_elevator(
                pax.origin_floor, rec["direction"], pax.priority
            )
            new_elevator = self.building.elevators[new_eid]
            rec["elevator_id"] = new_eid
            rec["reopt_count"] += 1
            if pax.priority == "EXPRESS":
                new_elevator.add_express_call(pax.origin_floor)
            else:
                new_elevator.add_to_queue(pax.origin_floor, rec["direction"])

        # --- Clean queues only if no one is still waiting at this floor ---
        still_waiting_here = any(
            r["state"] == "WAITING" and r["passenger"].origin_floor == floor
            for r in self._active_passengers.values()
        )
        if not still_waiting_here:
            if floor in elevator.up_queue:
                elevator.up_queue.remove(floor)
            if floor in elevator.down_queue:
                elevator.down_queue.remove(floor)
            if floor in elevator.express_queue:
                elevator.express_queue.remove(floor)
            # Use the passenger's original requested direction, not the
            # elevator's current travel direction, to avoid phantom calls.
            for cid in boarding_ids:
                rec = self._active_passengers.get(cid)
                if rec:
                    self.building.remove_call(
                        floor, rec["direction"], rec["passenger"].priority
                    )
                    break  # remove_call removes only the first match

    # ------------------------------------------------------------------
    # A* reoptimisation
    # ------------------------------------------------------------------
    def reoptimize_routes(self) -> None:
        """Run A* optimisation on every elevator's pending route."""
        for elevator in self.building.elevators:
            if not elevator.has_pending_stops():
                continue
            result = self.astar.optimize_route(elevator)
            if result["reopt_triggered"] and result["reopt_accepted"]:
                self.metrics["reopt_count"] += 1

    # ------------------------------------------------------------------
    # Dynamic weight adjustment
    # ------------------------------------------------------------------
    def adjust_weights(self) -> None:
        new_w = self.weight_adjuster.adjust_weights(force=True)
        history = self.weight_adjuster.get_history(1)
        if history:
            reasons = history[-1].get("reasons", [])
            reason_str = " | ".join(reasons) if reasons else "Routine"
            print(
                f"  [Weights] {reason_str} -> "
                f"dir={new_w.get('direction_bias', 0):.3f} "
                f"load={new_w.get('load_balance', 0):.3f} "
                f"dist={new_w.get('distance', 0):.3f}"
            )

    # ------------------------------------------------------------------
    # Traffic prediction
    # ------------------------------------------------------------------
    def update_prediction(self) -> None:
        self.traffic_predictor.update_prediction()
        forecast = self.traffic_predictor.forecast_next_n_minutes(5)
        print(
            f"  [Forecast] Next 5 min: ~{forecast['forecasted_volume']} calls "
            f"(conf={forecast['confidence']:.2f}) -> {forecast['recommendation']}"
        )

    # ------------------------------------------------------------------
    # Edge-case checks
    # ------------------------------------------------------------------
    def check_stuck_elevators(self) -> None:
        """Detect stuck elevators and redistribute their work.

        An elevator is considered stuck if it has pending stops and
        passengers on board but hasn't moved for > 300 s (idle_time_sec
        tracks continuous time without movement).
        """
        for e in self.building.elevators:
            has_work = e.has_pending_stops() or len(e.passengers) > 0
            if e.idle_time_sec > 300 and has_work:
                print(
                    f"  [STUCK] Elevator {e.elevator_id} idle "
                    f"{e.idle_time_sec:.0f}s with pending work -- "
                    f"marking non-operational & redistributing"
                )
                e.is_operational = False

                # Re-dispatch every waiting passenger assigned to this elevator
                for cid, rec in list(self._active_passengers.items()):
                    if rec["elevator_id"] == e.elevator_id and rec["state"] == "WAITING":
                        pax = rec["passenger"]
                        new_eid, _, _ = self.gbfs.assign_elevator(
                            pax.origin_floor, rec["direction"], pax.priority
                        )
                        new_elev = self.building.elevators[new_eid]
                        rec["elevator_id"] = new_eid
                        rec["reopt_count"] += 1
                        if pax.priority == "EXPRESS":
                            new_elev.add_express_call(pax.origin_floor)
                        else:
                            new_elev.add_to_queue(pax.origin_floor, rec["direction"])

    # ═══════════════════════════════════════════════════════════════════
    # Main simulation loop
    # ═══════════════════════════════════════════════════════════════════
    def run_simulation(self) -> dict:
        """Execute the full simulation and return a summary dict."""
        print("=" * 65)
        print("  ENTERPRISE ELEVATOR FLEET DISPATCHER - SIMULATION START")
        print("=" * 65)
        print(
            f"  Building : {self.building.num_floors} floors, "
            f"{len(self.building.elevators)} elevators"
        )
        print(f"  Duration : {self.total_steps} steps ({self.total_steps}s)")
        print(
            f"  SLA      : {self.weight_adjuster.sla_wait_target_sec}s avg wait"
        )
        print("=" * 65)

        for step in range(self.total_steps):
            self.current_step = step
            self.sim_time += timedelta(seconds=self.time_per_step)

            # 1. Generate calls
            calls = self.generate_calls()

            # 2. GBFS dispatch
            if calls:
                self.process_calls(calls)

            # 3. Move elevators
            self.move_elevators()

            # 4. A* reoptimisation (every 10 steps)
            if step % 10 == 0:
                self.reoptimize_routes()

            # 5. Dynamic weight adjustment (every 30 steps)
            if step % 30 == 0 and step > 0:
                self.adjust_weights()

            # 6. Traffic prediction (every 60 steps)
            if step % 60 == 0 and step > 0:
                self.update_prediction()

            # 7. Edge-case checks (every 120 steps)
            if step % 120 == 0:
                self.check_stuck_elevators()

            # 8. Progress report (every 300 steps)
            if step % 300 == 0 and step > 0:
                self._print_progress()

        # Finalise
        self.logger.close()
        summary = self._generate_summary()
        self._print_summary(summary)
        return summary

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def _print_progress(self) -> None:
        c = self.metrics
        completed = c["total_completed"]
        avg_wait = (
            c["total_wait_time"] / completed if completed > 0 else 0.0
        )
        print(
            f"  Step {self.current_step:>5}/{self.total_steps} | "
            f"Calls={c['total_calls']:>4} | "
            f"Completed={completed:>4} | "
            f"AvgWait={avg_wait:>5.1f}s | "
            f"MaxWait={c['max_wait_time']:>5.1f}s | "
            f"Distance={c['total_distance']:>5} floors"
        )

    def _generate_summary(self) -> dict:
        c = self.metrics
        completed = c["total_completed"]
        avg_wait = c["total_wait_time"] / completed if completed > 0 else 0.0
        sla_target = self.weight_adjuster.sla_wait_target_sec

        return {
            "total_duration_sec": self.total_steps * self.time_per_step,
            "total_calls_generated": c["total_calls"],
            "total_completed": completed,
            "emergency_calls": c["emergency_calls"],
            "capacity_rejections": c["capacity_rejections"],
            "avg_wait_time_sec": round(avg_wait, 2),
            "max_wait_time_sec": round(c["max_wait_time"], 2),
            "total_distance_floors": c["total_distance"],
            "total_reoptimisations": c["reopt_count"],
            "sla_target_sec": sla_target,
            "sla_met": avg_wait <= sla_target,
            "csv_rows_written": self.logger.total_rows_written,
        }

    @staticmethod
    def _print_summary(s: dict) -> None:
        print()
        print("=" * 65)
        print("  SIMULATION SUMMARY")
        print("=" * 65)
        for key, value in s.items():
            label = key.replace("_", " ").title()
            if isinstance(value, float):
                print(f"  {label:<30}: {value:>10.2f}")
            elif isinstance(value, bool):
                print(f"  {label:<30}: {'YES' if value else 'NO':>10}")
            else:
                print(f"  {label:<30}: {value!s:>10}")
        print("=" * 65)
        print(f"\n  CSV Output: elevator_training_data.csv -> {s['csv_rows_written']} rows x 21 columns")
        print("  Ready for ML training (Scikit-Learn RandomForest on gbfs_score vs wait_time)")
        print()


# ═══════════════════════════════════════════════════════════════════════════
# Interactive input helper
# ═══════════════════════════════════════════════════════════════════════════
def _prompt_int(label: str, default: int, min_val: int = 1) -> int:
    """Prompt the user for an integer value, showing the default."""
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            val = int(raw)
            if val < min_val:
                print(f"    [!]  Must be at least {min_val}. Try again.")
                continue
            return val
        except ValueError:
            print("    [!]  Please enter a valid number. Try again.")


def _prompt_float(label: str, default: float, min_val: float = 0.1) -> float:
    """Prompt the user for a float value, showing the default."""
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            val = float(raw)
            if val < min_val:
                print(f"    [!]  Must be at least {min_val}. Try again.")
                continue
            return val
        except ValueError:
            print("    [!]  Please enter a valid number. Try again.")


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # --- Parse --visualize flag ---
    _use_viz = "--visualize" in sys.argv
    _args = [a for a in sys.argv[1:] if a != "--visualize"]

    config_file = _args[0] if _args else os.path.join(
        _project_root, "config.json"
    )

    # Load base config
    with open(config_file, encoding="utf-8") as _fh:
        _base_config = json.load(_fh)

    # --- Interactive parameter input ---
    print()
    print("=" * 65)
    print("  ENTERPRISE ELEVATOR FLEET DISPATCHER -- CONFIGURATION")
    print("=" * 65)
    print("  Enter your simulation parameters below.")
    print("  Press ENTER to accept the default value shown in [brackets].")
    print("-" * 65)

    num_floors = _prompt_int(
        "Number of floors in the building",
        _base_config["simulation"]["building_floors"],
        min_val=2,
    )
    num_elevators = _prompt_int(
        "Number of elevators",
        _base_config["elevators"]["count"],
        min_val=1,
    )
    max_passengers = _prompt_int(
        "Max passengers per elevator",
        _base_config["elevators"]["max_passengers"],
        min_val=1,
    )
    duration_steps = _prompt_int(
        "Simulation duration (seconds)",
        _base_config["simulation"]["duration_steps"],
        min_val=10,
    )
    sla_target = _prompt_float(
        "SLA wait-time target (seconds)",
        _base_config["tuning"]["sla_wait_target_sec"],
        min_val=1.0,
    )
    
    scenario_case = _prompt_int(
        "Select Scenario (1: GBFS Auto-Dispatch, 2: Manual Elevator Selection)",
        1,
        min_val=1,
    )
    
    manual_mode_input = input("  Manual passenger mode (y/N) [N]: ").strip().lower()
    manual_mode = manual_mode_input == "y"

    # --- Apply user inputs to config ---
    _base_config["simulation"]["building_floors"] = num_floors
    _base_config["elevators"]["count"] = num_elevators
    _base_config["elevators"]["max_passengers"] = max_passengers
    _base_config["simulation"]["duration_steps"] = duration_steps
    _base_config["tuning"]["sla_wait_target_sec"] = sla_target
    _base_config["simulation"]["manual_mode"] = manual_mode
    _base_config["simulation"]["scenario_case"] = scenario_case

    # Write the updated config to a temporary file so the simulator reads it
    _temp_config_path = os.path.join(_project_root, "data", "_runtime_config.json")
    os.makedirs(os.path.dirname(_temp_config_path), exist_ok=True)
    with open(_temp_config_path, "w", encoding="utf-8") as _fh:
        json.dump(_base_config, _fh, indent=2)

    print("-" * 65)
    mode_label = "VISUAL" if _use_viz else "HEADLESS"
    print(f"  [OK] Configuration ready: {num_floors} floors, "
          f"{num_elevators} elevators, {duration_steps}s duration")
    print(f"  [OK] Mode: {mode_label}")
    print("=" * 65)
    print()

    # --- Run ---
    simulator = ElevatorFleetSimulator(_temp_config_path)

    if _use_viz:
        from backend.visualization import ElevatorVisualizer

        viz = ElevatorVisualizer(simulator)
        viz.run()
    else:
        simulator.run_simulation()
