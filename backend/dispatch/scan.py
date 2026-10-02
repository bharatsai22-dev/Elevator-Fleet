"""
SCAN Dispatcher — baseline strategy (Elevator Algorithm).

Classic SCAN / elevator algorithm:
  - Each elevator sweeps UP to the top, then DOWN to the bottom.
  - Picks up any passenger along the sweep direction.
  - The dispatcher picks the elevator whose current sweep path
    will encounter the call floor soonest.

This is a well-known real-world strategy and a strong baseline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.dispatch.base import DispatchStrategy

if TYPE_CHECKING:
    from backend.simulator.models import Building


class SCANDispatcher(DispatchStrategy):
    """SCAN (elevator algorithm) dispatcher for the elevator fleet."""

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
        Assign the elevator whose SCAN sweep will reach *floor* soonest.

        Scoring:
          - If the elevator is sweeping toward *floor* in the same
            direction, score = proximity (close = better).
          - If it will reach *floor* on the return sweep, add a
            penalty equal to the remaining distance to the boundary
            plus the distance back.
        """
        best_id: int | None = None
        best_cost: float = float("inf")
        candidates: list[dict] = []
        max_floor = self.building.num_floors
        min_floor = 1

        for elev in self.building.elevators:
            if not elev.is_operational:
                candidates.append({
                    "elevator_id": elev.elevator_id,
                    "scan_cost": float("inf"),
                    "reason": "NON-OPERATIONAL",
                })
                continue

            # Over-capacity check
            if (
                elev.occupancy_percent() > 85.0
                and priority == "NORMAL"
            ):
                candidates.append({
                    "elevator_id": elev.elevator_id,
                    "scan_cost": float("inf"),
                    "reason": "OVER_CAPACITY",
                })
                continue

            cost = self._scan_cost(
                elev.current_floor,
                elev.direction,
                floor,
                min_floor,
                max_floor,
            )

            candidates.append({
                "elevator_id": elev.elevator_id,
                "scan_cost": round(cost, 2),
                "reason": "OK",
            })

            if cost < best_cost or (
                cost == best_cost
                and (best_id is None or elev.elevator_id < best_id)
            ):
                best_cost = cost
                best_id = elev.elevator_id

        # Fallback
        if best_id is None:
            best_id = 0
            best_cost = abs(self.building.elevators[0].current_floor - floor)

        estimated_wait = best_cost * 2.0  # 2 sec per floor

        decision = {
            "call_floor": floor,
            "call_direction": direction,
            "call_priority": priority,
            "assigned_elevator": best_id,
            "best_score": round(-best_cost, 4),
            "estimated_wait": round(estimated_wait, 2),
            "weights_used": {},
            "candidates": candidates,
        }
        self._record_decision(decision)
        return best_id, estimated_wait, decision

    # ------------------------------------------------------------------
    # SCAN cost model
    # ------------------------------------------------------------------
    @staticmethod
    def _scan_cost(
        current: int,
        direction: str,
        target: int,
        min_floor: int,
        max_floor: int,
    ) -> float:
        """
        Number of floors the elevator must travel in SCAN order
        to reach *target*, assuming it continues in its current
        direction until it hits the boundary, then reverses.
        """
        if direction == "UP":
            if target >= current:
                # Target is ahead in the sweep
                return float(target - current)
            else:
                # Must go to top, reverse, then come back down
                return float((max_floor - current) + (max_floor - target))
        elif direction == "DOWN":
            if target <= current:
                # Target is ahead in the sweep
                return float(current - target)
            else:
                # Must go to bottom, reverse, then come back up
                return float((current - min_floor) + (target - min_floor))
        else:
            # IDLE — just use direct distance
            return float(abs(current - target))

    def _record_decision(self, decision: dict) -> None:
        self._decision_log.append(decision)
        if len(self._decision_log) > self._max_log_size:
            self._decision_log = self._decision_log[-self._max_log_size:]

    def get_recent_decisions(self, n: int = 20) -> list[dict]:
        """Return the last *n* dispatch decisions."""
        return self._decision_log[-n:]
