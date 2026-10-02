"""
Nearest-Lift Dispatcher — baseline strategy.

Always assigns the closest available elevator to the calling floor.
Ties are broken by lower elevator ID.

This is the simplest non-trivial strategy and serves as a baseline
for benchmarking the GBFS dispatcher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.dispatch.base import DispatchStrategy

if TYPE_CHECKING:
    from backend.simulator.models import Building


class NearestLiftDispatcher(DispatchStrategy):
    """Pick the closest operational elevator — no scoring, no fairness."""

    def __init__(self, building: "Building") -> None:
        self.building = building
        self._decision_log: list[dict] = []
        self._max_log_size: int = 500

    def assign_elevator(
        self,
        floor: int,
        direction: str,
        priority: str = "NORMAL",
    ) -> tuple[int, float, dict]:
        """
        Assign the nearest operational elevator.

        Preference order:
          1. Same-direction elevator closest to call floor
          2. IDLE elevator closest to call floor
          3. Any operational elevator closest to call floor
        """
        best_id: int | None = None
        best_dist: int = 999_999
        best_category: int = 3  # lower is better

        candidates: list[dict] = []

        for elev in self.building.elevators:
            if not elev.is_operational:
                candidates.append({
                    "elevator_id": elev.elevator_id,
                    "distance": -1,
                    "category": -1,
                    "reason": "NON-OPERATIONAL",
                })
                continue

            dist = abs(elev.current_floor - floor)

            # Determine category
            if elev.direction == direction:
                # Same direction, but only if it hasn't passed the floor
                can_serve = (
                    (direction == "UP" and elev.current_floor <= floor)
                    or (direction == "DOWN" and elev.current_floor >= floor)
                )
                cat = 1 if can_serve else 3
            elif elev.direction == "IDLE":
                cat = 2
            else:
                cat = 3

            # Occupancy check
            if (
                elev.occupancy_percent() > 85.0
                and priority == "NORMAL"
            ):
                cat = 4  # deprioritise heavily loaded

            candidates.append({
                "elevator_id": elev.elevator_id,
                "distance": dist,
                "category": cat,
                "reason": "OK",
            })

            if (cat, dist, elev.elevator_id) < (
                best_category, best_dist, best_id if best_id is not None else 999
            ):
                best_category = cat
                best_dist = dist
                best_id = elev.elevator_id

        # Fallback
        if best_id is None:
            best_id = 0
            best_dist = abs(self.building.elevators[0].current_floor - floor)

        estimated_wait = best_dist * 2.0 + 5.0

        decision = {
            "call_floor": floor,
            "call_direction": direction,
            "call_priority": priority,
            "assigned_elevator": best_id,
            "best_score": round(-best_dist, 4),
            "estimated_wait": round(estimated_wait, 2),
            "weights_used": {},
            "candidates": candidates,
        }
        self._record_decision(decision)
        return best_id, estimated_wait, decision

    def _record_decision(self, decision: dict) -> None:
        self._decision_log.append(decision)
        if len(self._decision_log) > self._max_log_size:
            self._decision_log = self._decision_log[-self._max_log_size:]

    def get_recent_decisions(self, n: int = 20) -> list[dict]:
        """Return the last *n* dispatch decisions."""
        return self._decision_log[-n:]
