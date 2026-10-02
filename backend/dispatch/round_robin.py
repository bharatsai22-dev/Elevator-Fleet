"""
Round-Robin Dispatcher — baseline strategy.

Cycles through elevators in order (0, 1, 2, 3, 0, 1, …),
regardless of distance, direction, or load.

This is the simplest possible strategy and serves as the
lower-bound baseline for benchmarking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.dispatch.base import DispatchStrategy

if TYPE_CHECKING:
    from backend.simulator.models import Building


class RoundRobinDispatcher(DispatchStrategy):
    """Assign elevators in a fixed cyclic order."""

    def __init__(self, building: "Building") -> None:
        self.building = building
        self._next_index: int = 0
        self._decision_log: list[dict] = []
        self._max_log_size: int = 500

    def assign_elevator(
        self,
        floor: int,
        direction: str,
        priority: str = "NORMAL",
    ) -> tuple[int, float, dict]:
        """
        Assign the next elevator in the cycle.

        Skips non-operational elevators.
        """
        n = len(self.building.elevators)
        attempts = 0
        chosen_id = self._next_index

        # Find next operational elevator
        while attempts < n:
            elev = self.building.elevators[chosen_id]
            if elev.is_operational:
                break
            chosen_id = (chosen_id + 1) % n
            attempts += 1
        else:
            # All non-operational; fall back to elevator 0
            chosen_id = 0

        # Advance the pointer for next call
        self._next_index = (chosen_id + 1) % n

        elevator = self.building.elevators[chosen_id]
        dist = abs(elevator.current_floor - floor)
        estimated_wait = dist * 2.0 + len(elevator.passengers) * 5.0

        decision = {
            "call_floor": floor,
            "call_direction": direction,
            "call_priority": priority,
            "assigned_elevator": chosen_id,
            "best_score": 0.0,
            "estimated_wait": round(estimated_wait, 2),
            "weights_used": {},
            "candidates": [
                {
                    "elevator_id": i,
                    "selected": i == chosen_id,
                }
                for i in range(n)
            ],
        }
        self._record_decision(decision)
        return chosen_id, estimated_wait, decision

    def _record_decision(self, decision: dict) -> None:
        self._decision_log.append(decision)
        if len(self._decision_log) > self._max_log_size:
            self._decision_log = self._decision_log[-self._max_log_size:]

    def get_recent_decisions(self, n: int = 20) -> list[dict]:
        """Return the last *n* dispatch decisions."""
        return self._decision_log[-n:]
