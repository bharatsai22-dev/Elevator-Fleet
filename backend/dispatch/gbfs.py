"""
GBFS (Greedy Best-First Search) Central Fleet Dispatcher.

Assigns incoming elevator calls to the optimal elevator using a
multi-objective, wait-time-optimised heuristic.

Heuristic scoring (Phase 2 — Enhanced):
    Score = (W1 × direction_bias)
          + (W2 × load_balance)
          + (W3 × distance)
          + (W4 × wait_time)
          + (W5 × emergency_bonus)
          + (W6 × fairness)

Enhancements over Phase 1:
    - Positional direction awareness (can the elevator actually reach
      the call floor without reversing?)
    - En-route bonus: elevator already heading through the call floor
    - Queue-depth penalty: penalise elevators with long queues
    - Starvation-aware fairness: passengers waiting > 60 % SLA get
      exponentially increasing priority
"""

from __future__ import annotations

import math
import sys
from typing import TYPE_CHECKING

from backend.dispatch.base import DispatchStrategy

if TYPE_CHECKING:
    from backend.simulator.models import Building


class GBFSDispatcher(DispatchStrategy):
    """Greedy Best-First Search dispatcher for the elevator fleet."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, building: "Building") -> None:
        self.building = building

        # Initial weights for the requested f(e) formula
        self.weights: dict[str, float] = {
            "w1": -0.5,  # Negative because more waiting is worse
            "w2": 0.8,   # Positive because more capacity is better
            "w3": 1.2,   # Positive because it's subtracted: - (Distance Cost * W3)
        }

        # Hard bounds used by the Dynamic Weight Adjuster
        self.weight_bounds: dict[str, tuple[float, float]] = {
            "w1": (-1.0, 0.0),
            "w2": (0.1, 1.5),
            "w3": (0.5, 2.0),
        }

        # Occupancy threshold — elevators above this % skip NORMAL calls
        self.occupancy_threshold_pct: float = 85.0

        # Queue-depth penalty factor (applied per queued stop)
        self.queue_depth_penalty: float = 0.03

        # SLA target (seconds) — used for starvation calculation
        self.sla_target_sec: float = 45.0

        # Decision log (recent N for GUI / debugging)
        self._decision_log: list[dict] = []
        self._max_log_size: int = 500

        # Starvation tracking: call_id -> request_time (seconds since epoch)
        self._pending_waits: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Starvation tracking
    # ------------------------------------------------------------------
    def register_pending_call(
        self, call_id: str, request_time_sec: float
    ) -> None:
        """Register a new call so its waiting time can be tracked."""
        self._pending_waits[call_id] = request_time_sec

    def complete_call(self, call_id: str) -> None:
        """Remove a call from the starvation tracker."""
        self._pending_waits.pop(call_id, None)

    def _max_pending_wait(self, current_time_sec: float) -> float:
        """Return the longest time any pending call has been waiting."""
        if not self._pending_waits:
            return 0.0
        return max(
            current_time_sec - t for t in self._pending_waits.values()
        )

    # ------------------------------------------------------------------
    # Main assignment entry-point
    # ------------------------------------------------------------------
    def assign_elevator(
        self,
        floor: int,
        direction: str,
        priority: str = "NORMAL",
    ) -> tuple[int, float, dict]:
        """
        Assign the best elevator to a call.

        Args:
            floor:     The floor the call originates from.
            direction: "UP" or "DOWN".
            priority:  "NORMAL" or "EXPRESS".

        Returns:
            (elevator_id, estimated_wait_sec, decision_details)
        """
        best_id: int | None = None
        best_score: float = -float("inf")
        best_wait: float = 0.0
        candidate_scores: list[dict] = []

        for elevator in self.building.elevators:
            if not elevator.is_operational:
                candidate_scores.append(
                    {
                        "elevator_id": elevator.elevator_id,
                        "score": -float("inf"),
                        "reason": "NON-OPERATIONAL",
                    }
                )
                continue

            # ---- Calculate Requested Heuristic Terms ----
            # Waiting Count (passengers on board + queued stops)
            waiting_count = len(elevator.passengers) + len(elevator.up_queue) + len(elevator.down_queue)
            
            # Available Capacity
            available_capacity = elevator.max_passengers - len(elevator.passengers)
            
            # Distance Cost
            distance_cost = abs(elevator.current_floor - floor)

            # ---- Composite score: f(e) = (Waiting Count * W1) + (Available Capacity * W2) - (Distance Cost * W3) ----
            score = (
                (waiting_count * self.weights["w1"])
                + (available_capacity * self.weights["w2"])
                - (distance_cost * self.weights["w3"])
            )

            # ---- Occupancy constraint ----
            reason = "OK"
            if (
                elevator.occupancy_percent() > self.occupancy_threshold_pct
                and priority == "NORMAL"
            ):
                score = -float("inf")
                reason = "OVER_CAPACITY (>85%)"

            # ---- EXPRESS override ----
            if priority == "EXPRESS":
                score += 100.0  # massive boost

            # ---- Estimated wait (improved heuristic) ----
            estimated_wait = self._estimate_wait(elevator, floor)

            candidate_scores.append(
                {
                    "elevator_id": elevator.elevator_id,
                    "score": round(score, 4),
                    "waiting_count": waiting_count,
                    "available_capacity": available_capacity,
                    "distance_cost": distance_cost,
                    "estimated_wait": round(estimated_wait, 2),
                    "reason": reason,
                }
            )

            if score > best_score:
                best_score = score
                best_id = elevator.elevator_id
                best_wait = estimated_wait

        # Fallback: if every elevator was disqualified, pick least loaded
        if best_id is None:
            best_id = min(
                range(len(self.building.elevators)),
                key=lambda i: self.building.elevators[i].total_load_kg,
            )
            best_wait = 60.0

        # Build decision record
        decision = {
            "call_floor": floor,
            "call_direction": direction,
            "call_priority": priority,
            "assigned_elevator": best_id,
            "best_score": round(best_score, 4),
            "estimated_wait": round(best_wait, 2),
            "weights_used": self.weights.copy(),
            "candidates": candidate_scores,
        }
        self._record_decision(decision)

        return best_id, best_wait, decision

    # ------------------------------------------------------------------
    # Enhanced direction scoring (Phase 2A)
    # ------------------------------------------------------------------
    def _direction_score(
        self, elevator, floor: int, direction: str
    ) -> float:
        """
        Score how well the elevator's current state matches the call.

        Considers:
          - Direction match (same / idle / opposite)
          - Positional feasibility (can it reach the floor without reversing?)
          - En-route bonus (floor is on the elevator's current path)
        """
        e_floor = elevator.current_floor
        e_dir = elevator.direction

        # --- Base direction match ---
        if e_dir == direction:
            base = 1.0
        elif e_dir == "IDLE":
            base = 0.5
        else:
            base = -0.5

        # --- Positional feasibility ---
        # If elevator is moving UP but the call is below, it must reverse first
        if e_dir == "UP" and floor < e_floor:
            base -= 0.3
        elif e_dir == "DOWN" and floor > e_floor:
            base -= 0.3

        # --- En-route bonus ---
        # Elevator is heading toward the call floor AND the call direction matches
        is_en_route = (
            (e_dir == "UP" and floor >= e_floor and direction == "UP")
            or (e_dir == "DOWN" and floor <= e_floor and direction == "DOWN")
        )
        if is_en_route:
            base += 0.4

        return max(-1.0, min(1.5, base))  # clamp to [-1.0, 1.5]

    # ------------------------------------------------------------------
    # Fairness / starvation scoring (Phase 2B)
    # ------------------------------------------------------------------
    def _fairness_score(self, elevator, call_floor: int) -> float:
        """
        Score based on how quickly this elevator could reduce starvation.

        Returns a higher score for elevators that are closer to
        passengers who have been waiting the longest.
        """
        if not self._pending_waits:
            return 0.5  # neutral when no tracking data

        # Find the longest-waiting call's floor from building queues
        longest_wait_floor = None
        longest_wait_time = 0.0

        # Check up_calls and down_calls for the oldest timestamp
        for call_list in [
            self.building.up_calls,
            self.building.down_calls,
            self.building.express_calls,
        ]:
            for floor_num, timestamp in call_list:
                from datetime import datetime
                age = (datetime.now() - timestamp).total_seconds()
                if age > longest_wait_time:
                    longest_wait_time = age
                    longest_wait_floor = floor_num

        if longest_wait_floor is None:
            return 0.5

        # Starvation multiplier: exponential increase when past 60% of SLA
        starvation_ratio = longest_wait_time / max(self.sla_target_sec, 1.0)
        if starvation_ratio > 0.6:
            urgency = 1.0 + math.exp(starvation_ratio - 1.0)
        else:
            urgency = 1.0

        # How close is this elevator to the starving passenger?
        max_dist = max(self.building.num_floors - 1, 1)
        proximity = 1.0 - (
            abs(elevator.current_floor - longest_wait_floor) / max_dist
        )

        return min(proximity * urgency, 2.0)  # cap at 2.0

    # ------------------------------------------------------------------
    # Improved wait estimation
    # ------------------------------------------------------------------
    def _estimate_wait(self, elevator, call_floor: int) -> float:
        """
        Estimate wait time in seconds, accounting for queued stops
        and passenger boarding time.
        """
        manhattan = abs(elevator.current_floor - call_floor)
        # 2 seconds per floor, plus 3 seconds per intermediate stop,
        # plus 5 seconds per on-board passenger boarding overhead
        intermediate_stops = 0
        if elevator.direction == "UP":
            intermediate_stops = sum(
                1 for f in elevator.up_queue
                if elevator.current_floor < f < call_floor
            )
        elif elevator.direction == "DOWN":
            intermediate_stops = sum(
                1 for f in elevator.down_queue
                if call_floor < f < elevator.current_floor
            )

        return (
            manhattan * 2.0
            + intermediate_stops * 3.0
            + len(elevator.passengers) * 1.5
        )

    # ------------------------------------------------------------------
    # Weight management (called by DynamicWeightAdjuster)
    # ------------------------------------------------------------------
    def set_weights(self, new_weights: dict[str, float]) -> None:
        """Apply new weights, clamping to configured bounds."""
        for key, value in new_weights.items():
            if key in self.weights:
                lo, hi = self.weight_bounds.get(key, (0.0, 1.0))
                self.weights[key] = max(lo, min(hi, value))

    def get_current_weights(self) -> dict[str, float]:
        """Return a snapshot of the current weight vector."""
        return self.weights.copy()

    # ------------------------------------------------------------------
    # Decision log
    # ------------------------------------------------------------------
    def _record_decision(self, decision: dict) -> None:
        self._decision_log.append(decision)
        if len(self._decision_log) > self._max_log_size:
            self._decision_log = self._decision_log[-self._max_log_size:]

    def get_recent_decisions(self, n: int = 20) -> list[dict]:
        """Return the last *n* dispatch decisions."""
        return self._decision_log[-n:]
