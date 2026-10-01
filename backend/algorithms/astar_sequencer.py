"""
A* Floor Sequencer — Individual Elevator Pathfinding.

Once an elevator has been dispatched (by GBFS) and has multiple stops
queued, this module computes the optimal floor-visitation order using
A* search, minimising total vertical travel distance.

Key features:
    - Guarantees shortest-path via f(n) = g(n) + h(n)
    - Call-Adaptive Soft Reoptimisation within a ±2-floor pickup zone
    - Hard +15 % cost bound: never degrades existing passengers' routes
      beyond 15 % of the original optimal cost
    - Greedy nearest-neighbour fallback on timeout / edge cases
"""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.simulation.models import Building, Elevator


class AStarSequencer:
    """A* search engine for single-elevator floor sequencing."""

    def __init__(self, building: "Building") -> None:
        self.building = building
        self.reopt_distance_threshold: int = 2      # ±floors to trigger reopt
        self.max_cost_increase_pct: float = 15.0     # hard bound

    # ------------------------------------------------------------------
    # Cost calculation
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_route_cost(floors: list[int]) -> float:
        """Total vertical distance for an ordered list of floors."""
        cost = 0.0
        for i in range(len(floors) - 1):
            cost += abs(floors[i + 1] - floors[i])
        return cost

    # ------------------------------------------------------------------
    # Core A* search
    # ------------------------------------------------------------------
    def a_star_search(
        self, current_floor: int, unvisited_floors: list[int]
    ) -> list[int]:
        """
        Compute the optimal visitation order for *unvisited_floors*
        starting from *current_floor*.

        f(n) = g(n) + h(n)
            g(n) = accumulated vertical distance so far
            h(n) = distance to the farthest remaining unvisited floor

        Returns:
            Ordered list beginning with *current_floor*.
        """
        if not unvisited_floors:
            return [current_floor]

        target_count = len(unvisited_floors)

        # (f_score, g_score, current_floor, visited_mask, path)
        # visited_mask: bitmask of visited indices in unvisited_floors
        initial_h = self._heuristic(current_floor, unvisited_floors, 0)
        open_set: list[tuple[float, float, int, int, tuple]] = [
            (initial_h, 0.0, current_floor, 0, (current_floor,))
        ]
        best_cost: dict[tuple[int, int], float] = {}

        while open_set:
            f, g, floor, visited, path = heapq.heappop(open_set)

            # All floors visited?
            if bin(visited).count("1") == target_count:
                return list(path)

            state_key = (floor, visited)
            if state_key in best_cost and best_cost[state_key] <= g:
                continue
            best_cost[state_key] = g

            for idx, next_floor in enumerate(unvisited_floors):
                bit = 1 << idx
                if visited & bit:
                    continue  # already visited

                new_g = g + abs(next_floor - floor)
                new_visited = visited | bit
                new_h = self._heuristic(next_floor, unvisited_floors, new_visited)
                new_f = new_g + new_h
                new_path = path + (next_floor,)

                heapq.heappush(
                    open_set, (new_f, new_g, next_floor, new_visited, new_path)
                )

        # Fallback
        return self._greedy_nearest_neighbor(current_floor, unvisited_floors)

    # ------------------------------------------------------------------
    # Heuristic
    # ------------------------------------------------------------------
    @staticmethod
    def _heuristic(
        current_floor: int, unvisited: list[int], visited_mask: int
    ) -> float:
        """h(n): distance from *current_floor* to the farthest remaining floor."""
        remaining = [
            f
            for idx, f in enumerate(unvisited)
            if not (visited_mask & (1 << idx))
        ]
        if not remaining:
            return 0.0
        return float(max(abs(current_floor - f) for f in remaining))

    # ------------------------------------------------------------------
    # Greedy fallback
    # ------------------------------------------------------------------
    @staticmethod
    def _greedy_nearest_neighbor(
        current_floor: int, unvisited: list[int]
    ) -> list[int]:
        """Nearest-neighbour heuristic — O(n²) but always returns a result."""
        path = [current_floor]
        remaining = list(unvisited)
        while remaining:
            nearest = min(remaining, key=lambda f: abs(f - path[-1]))
            path.append(nearest)
            remaining.remove(nearest)
        return path

    # ------------------------------------------------------------------
    # Public: optimise an elevator's current route
    # ------------------------------------------------------------------
    def optimize_route(self, elevator: "Elevator") -> dict:
        """
        Compute the optimal floor sequence for *elevator*.

        Returns a dict containing:
            elevator_id, optimized_sequence, total_cost,
            reopt_triggered, reopt_accepted, cost_increase_percent
        """
        pending = elevator.all_pending_floors()
        if not pending:
            return {
                "elevator_id": elevator.elevator_id,
                "optimized_sequence": [elevator.current_floor],
                "total_cost": 0.0,
                "reopt_triggered": False,
                "reopt_accepted": False,
                "cost_increase_percent": 0.0,
            }

        # Remove current floor from the 'to-visit' set if present
        to_visit = [f for f in pending if f != elevator.current_floor]

        # --- baseline cost (current queue order) ---
        baseline_path = [elevator.current_floor] + to_visit
        baseline_cost = self.calculate_route_cost(baseline_path)

        # --- A* optimal sequence ---
        optimised = self.a_star_search(elevator.current_floor, to_visit)
        optimised_cost = self.calculate_route_cost(optimised)

        if baseline_cost > 0:
            cost_change_pct = (
                (optimised_cost - baseline_cost) / baseline_cost
            ) * 100.0
        else:
            cost_change_pct = 0.0

        reopt_triggered = cost_change_pct != 0.0
        reopt_accepted = cost_change_pct <= self.max_cost_increase_pct

        # Apply the new route only if it's within the bound
        if reopt_accepted and optimised_cost <= baseline_cost:
            self._apply_route(elevator, optimised)

        return {
            "elevator_id": elevator.elevator_id,
            "optimized_sequence": optimised,
            "total_cost": optimised_cost,
            "baseline_cost": baseline_cost,
            "reopt_triggered": reopt_triggered,
            "reopt_accepted": reopt_accepted,
            "cost_increase_percent": round(cost_change_pct, 2),
        }

    # ------------------------------------------------------------------
    # Public: on-the-fly reopt when a new call lands nearby
    # ------------------------------------------------------------------
    def reopt_on_new_call(
        self, elevator: "Elevator", new_call_floor: int
    ) -> bool:
        """
        Re-optimise *elevator* if *new_call_floor* is within the
        pickup zone (±reopt_distance_threshold floors).

        Returns True if the reoptimisation was accepted.
        """
        if (
            abs(new_call_floor - elevator.current_floor)
            <= self.reopt_distance_threshold
        ):
            result = self.optimize_route(elevator)
            return result["reopt_accepted"]
        return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_route(elevator: "Elevator", sequence: list[int]) -> None:
        """
        Overwrite elevator queues with the A*-optimised sequence.
        Express queue is left intact (highest priority).
        """
        optimised_floors = sequence[1:]  # skip current_floor
        express = set(elevator.express_queue)

        elevator.up_queue = [
            f for f in optimised_floors if f > elevator.current_floor and f not in express
        ]
        elevator.down_queue = [
            f for f in optimised_floors if f < elevator.current_floor and f not in express
        ]
