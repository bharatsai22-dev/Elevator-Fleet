"""
Traffic Generator — scenario-driven passenger call generation.

Provides four traffic scenarios, each modelling a different time
of day in a typical office building:

    morning_rush    – 80% UP from floor 1, λ=4.0 calls/step
    lunch_peak      – 50/50 UP/DOWN, mid-floor triangular, λ=3.0
    evening_rush    – 80% DOWN to floor 1, λ=3.5
    random_uniform  – uniform random origin/dest, λ=2.0

All scenarios are fully deterministic per seed.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from backend.simulator.models import Building


# ═══════════════════════════════════════════════════════════════════════════
# Scenario registry
# ═══════════════════════════════════════════════════════════════════════════
_SCENARIOS = {
    "morning_rush": {
        "description": "80% UP from ground floor, heavy traffic",
        "lambda": 4.0,
        "up_bias": 0.80,
        "origin_bias": "ground",
    },
    "lunch_peak": {
        "description": "50/50 UP/DOWN, mid-floor triangular distribution",
        "lambda": 3.0,
        "up_bias": 0.50,
        "origin_bias": "middle",
    },
    "evening_rush": {
        "description": "80% DOWN to ground floor, heavy traffic",
        "lambda": 3.5,
        "up_bias": 0.20,
        "origin_bias": "upper",
    },
    "random_uniform": {
        "description": "Uniform random origin/destination, moderate traffic",
        "lambda": 2.0,
        "up_bias": 0.50,
        "origin_bias": "uniform",
    },
}


def get_scenario_names() -> list[str]:
    """Return the list of available scenario names."""
    return list(_SCENARIOS.keys())


# ═══════════════════════════════════════════════════════════════════════════
# Traffic Generator
# ═══════════════════════════════════════════════════════════════════════════
class TrafficGenerator:
    """Generates passenger calls according to a selected scenario."""

    def __init__(
        self,
        building: "Building",
        config: dict,
        rng: np.random.Generator,
        scenario_name: str | None = None,
    ) -> None:
        self.building = building
        self.config = config
        self.rng = rng
        self.scenario_name = scenario_name or "random_uniform"
        self.scenario = _SCENARIOS.get(self.scenario_name, _SCENARIOS["random_uniform"])

        self._call_counter: int = 0

    # ------------------------------------------------------------------
    # Main generation
    # ------------------------------------------------------------------
    def generate_calls(
        self, sim_time: datetime, time_per_step: float
    ) -> list[tuple[int, str, str, int]]:
        """
        NHPP (Non-Homogeneous Poisson Process) generation.
        Traffic swells and tapers using a diurnal sine wave approximation.
        """
        base_lam = self.scenario["lambda"]

        # 1. Non-Homogeneous Poisson Process (NHPP)
        # Simulate traffic swell and taper over a typical hour-long wave
        # The wave cycles every 3600 seconds, scaling the lambda continuously.
        cycle_position = (sim_time.timestamp() % 3600) / 3600.0
        # Sine wave from 0.2x to 1.8x the base rate
        time_modifier = 1.0 + 0.8 * np.sin(2 * np.pi * cycle_position)
        
        dynamic_lam = base_lam * time_modifier
        
        # Poisson draw based on the dynamic lambda
        num_calls = int(self.rng.poisson(dynamic_lam * time_per_step / 10.0))

        calls: list[tuple[int, str, str, int]] = []
        for _ in range(num_calls):
            call = self._generate_one_call()
            if call is not None:
                calls.append(call)

        return calls

    # ------------------------------------------------------------------
    # Single call generation (scenario-aware)
    # ------------------------------------------------------------------
    def _build_od_matrix(self):
        """Construct an Origin-Destination (OD) Matrix for realistic routing."""
        num_floors = self.building.num_floors
        bias = self.scenario["origin_bias"]
        up_bias = self.scenario["up_bias"]

        matrix = np.zeros((num_floors, num_floors))
        for i in range(1, num_floors + 1):
            for j in range(1, num_floors + 1):
                if i == j:
                    continue
                
                # Base weight
                weight = 1.0
                
                # Apply Up/Down Bias
                if j > i:
                    weight *= up_bias
                else:
                    weight *= (1.0 - up_bias)

                # Apply Specific Scenario Bias
                if bias == "ground":
                    if i == 1: weight *= 10.0
                    if j == 1: weight *= 2.0
                elif bias == "upper":
                    if i > num_floors // 2: weight *= 4.0
                    if j == 1: weight *= 6.0
                elif bias == "middle":
                    # Higher probability for mid-floors
                    mid = num_floors / 2.0
                    dist_i = abs(i - mid) / mid
                    dist_j = abs(j - mid) / mid
                    weight *= (1.5 - dist_i) * (1.5 - dist_j)

                matrix[i - 1, j - 1] = weight

        # Normalize the matrix to probabilities
        return matrix / matrix.sum()

    def _generate_one_call(self) -> tuple[int, str, str, int] | None:
        """Generate one call based on the OD Matrix."""
        if not hasattr(self, "od_matrix"):
            self.od_matrix = self._build_od_matrix()

        num_floors = self.building.num_floors
        flat_matrix = self.od_matrix.flatten()
        
        # Sample a specific Origin-Destination pair
        idx = self.rng.choice(len(flat_matrix), p=flat_matrix)
        origin = (idx // num_floors) + 1
        dest = (idx % num_floors) + 1

        direction = "UP" if dest > origin else "DOWN"

        # Priority: small chance of EXPRESS
        if self.rng.random() < 0.03:
            priority = "EXPRESS"
        else:
            priority = "NORMAL"

        self._call_counter += 1
        return (origin, direction, priority, dest)
