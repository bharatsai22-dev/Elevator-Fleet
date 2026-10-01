"""
GBFS (Greedy Best-First Search) Central Fleet Dispatcher.

Assigns incoming elevator calls to the optimal elevator using a
multi-objective, wait-time-optimized heuristic.

Heuristic scoring:
    Score = (W1 × direction_bias)
          + (W2 × load_balance)
          + (W3 × distance)
          + (W4 × wait_time)
          + (W5 × emergency_bonus)

Key behaviours:
    - UP calls prioritise elevators already moving UP
    - DOWN calls prioritise elevators already moving DOWN
    - EXPRESS calls receive a massive score boost (+100)
    - Elevators >85 % loaded are disqualified for NORMAL calls
    - EXPRESS calls can override occupancy limits
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.simulation.models import Building


class GBFSDispatcher:
    """Greedy Best-First Search dispatcher for the elevator fleet."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, building: "Building") -> None:
        self.building = building

        # Initial weights (optimised for passenger wait-time)
        self.weights: dict[str, float] = {
            "direction_bias": 0.40,
            "load_balance": 0.25,
            "distance": 0.20,
            "wait_time": 0.10,
            "emergency_bonus": 0.05,
        }

        # Hard bounds used by the Dynamic Weight Adjuster
        self.weight_bounds: dict[str, tuple[float, float]] = {
            "direction_bias": (0.25, 0.50),
            "load_balance": (0.15, 0.40),
            "distance": (0.10, 0.30),
            "wait_time": (0.05, 0.20),
            "emergency_bonus": (0.02, 0.10),
        }

        # Occupancy threshold — elevators above this % skip NORMAL calls
        self.occupancy_threshold_pct: float = 85.0

        # Decision log (recent N for GUI / debugging)
        self._decision_log: list[dict] = []
        self._max_log_size: int = 500

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

            # ---- 1. Direction bias (higher → better) ----
            if elevator.direction == direction:
                dir_score = 1.0
            elif elevator.direction == "IDLE":
                dir_score = 0.5
            else:
                dir_score = -0.5

            # ---- 2. Load balance (higher → less loaded → better) ----
            load_score = 1.0 - (elevator.occupancy_percent() / 100.0)

            # ---- 3. Distance (closer → better, normalised to 0-1) ----
            max_dist = max(self.building.num_floors - 1, 1)
            manhattan = abs(elevator.current_floor - floor)
            distance_score = 1.0 - (manhattan / max_dist)

            # ---- 4. Wait-time proxy (fewer on-board pax → better) ----
            max_pax = max(elevator.max_passengers, 1)
            wait_score = 1.0 - (len(elevator.passengers) / max_pax)

            # ---- 5. Emergency bonus ----
            emergency_bonus = 1.0 if priority == "EXPRESS" else 0.0

            # ---- Composite score ----
            score = (
                self.weights["direction_bias"] * dir_score
                + self.weights["load_balance"] * load_score
                + self.weights["distance"] * distance_score
                + self.weights["wait_time"] * wait_score
                + self.weights["emergency_bonus"] * emergency_bonus
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

            # ---- Estimated wait (simple heuristic) ----
            estimated_wait = (manhattan * 2.0) + (len(elevator.passengers) * 5.0)

            candidate_scores.append(
                {
                    "elevator_id": elevator.elevator_id,
                    "score": round(score, 4),
                    "dir_score": round(dir_score, 4),
                    "load_score": round(load_score, 4),
                    "distance_score": round(distance_score, 4),
                    "wait_score": round(wait_score, 4),
                    "emergency_bonus": round(emergency_bonus, 4),
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
    # Weight management (called by DynamicWeightAdjuster)
    # ------------------------------------------------------------------
    def set_weights(self, new_weights: dict[str, float]) -> None:
        """Apply new weights, clamping to configured bounds."""
        for key, value in new_weights.items():
            if key in self.weights:
                lo, hi = self.weight_bounds[key]
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
