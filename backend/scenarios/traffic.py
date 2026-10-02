"""
Traffic Generator — scenario-based call generation.

Provides 4 named traffic scenarios with deterministic call sequences
(given a seed) so every dispatch strategy receives identical traffic
for fair benchmarking.

Scenarios:
    morning_rush   — 80 % UP from floor 1, heavy Poisson rate
    lunch_peak     — 50/50 UP/DOWN, mid-floor activity
    evening_rush   — 80 % DOWN to floor 1
    random_uniform — uniform random origins/destinations all day
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from backend.simulator.models import Building


# ---------------------------------------------------------------------------
# Scenario profiles
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, dict] = {
    "morning_rush": {
        "description": "Heavy UP traffic from ground floor (7–10 AM rush)",
        "lambda_base": 4.0,
        "ground_up_pct": 0.80,     # 80 % of calls start at floor 1 going UP
        "express_pct": 0.05,
    },
    "lunch_peak": {
        "description": "Bidirectional traffic, mid-floors active (12–2 PM)",
        "lambda_base": 3.0,
        "ground_up_pct": 0.0,      # no ground-floor bias
        "express_pct": 0.03,
    },
    "evening_rush": {
        "description": "Heavy DOWN traffic to ground floor (5–7 PM rush)",
        "lambda_base": 3.5,
        "ground_down_pct": 0.80,   # 80 % go DOWN to floor 1
        "express_pct": 0.04,
    },
    "random_uniform": {
        "description": "Uniform random traffic throughout the day",
        "lambda_base": 2.0,
        "ground_up_pct": 0.0,
        "express_pct": 0.05,
    },
}


class TrafficGenerator:
    """Generates elevator calls based on traffic patterns and Poisson arrivals."""

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

        # If a scenario is explicitly requested, use it; otherwise fall
        # back to the config-driven approach (backward compatible)
        self.scenario_name = scenario_name
        self.scenario = SCENARIOS.get(scenario_name) if scenario_name else None

    # ------------------------------------------------------------------
    # Scenario selection at runtime
    # ------------------------------------------------------------------
    def set_scenario(self, scenario_name: str) -> None:
        """Switch to a named scenario (for benchmark runs)."""
        if scenario_name not in SCENARIOS:
            raise ValueError(
                f"Unknown scenario '{scenario_name}'. "
                f"Choose from: {list(SCENARIOS.keys())}"
            )
        self.scenario_name = scenario_name
        self.scenario = SCENARIOS[scenario_name]

    # ------------------------------------------------------------------
    # Traffic intensity
    # ------------------------------------------------------------------
    def _get_lambda_multiplier(self, hour: int) -> float:
        """Return the Poisson λ multiplier for the current hour."""
        tc = self.config.get("traffic", {})
        for mode_name, mode in tc.items():
            if not isinstance(mode, dict):
                continue
            start = mode.get("start_hour", 0)
            end = mode.get("end_hour", 24)
            if start < end:
                if start <= hour < end:
                    return mode.get("lambda_multiplier", 1.0)
            else:  # wraps midnight
                if hour >= start or hour < end:
                    return mode.get("lambda_multiplier", 1.0)
        return 1.0  # default

    # ------------------------------------------------------------------
    # Call generation
    # ------------------------------------------------------------------
    def generate_calls(
        self,
        sim_time: datetime,
        time_per_step: float,
    ) -> list[tuple[int, str, str, int]]:
        """
        Generate random calls for the current simulation step.

        Args:
            sim_time:       Current simulation time.
            time_per_step:  Seconds per simulation step.

        Returns:
            List of (floor, direction, priority, destination) tuples.
        """
        if self.config["simulation"].get("manual_mode", False):
            return []

        max_floor = self.config["simulation"]["building_floors"]

        # Choose generation method based on whether a scenario is active
        if self.scenario is not None:
            return self._generate_scenario_calls(
                sim_time, time_per_step, max_floor
            )
        return self._generate_config_calls(sim_time, time_per_step, max_floor)

    # ------------------------------------------------------------------
    # Config-driven generation (backward compatible)
    # ------------------------------------------------------------------
    def _generate_config_calls(
        self, sim_time: datetime, time_per_step: float, max_floor: int
    ) -> list[tuple[int, str, str, int]]:
        """Original config-based call generation."""
        hour = sim_time.hour
        lam = 2.0 * self._get_lambda_multiplier(hour) / 60.0 * time_per_step
        num_calls = int(self.rng.poisson(lam))

        calls: list[tuple[int, str, str, int]] = []
        for _ in range(num_calls):
            floor = int(self.rng.integers(1, max_floor + 1))
            dest = floor
            while dest == floor:
                dest = int(self.rng.integers(1, max_floor + 1))

            direction = "UP" if dest > floor else "DOWN"
            priority = "EXPRESS" if self.rng.random() < 0.05 else "NORMAL"
            calls.append((floor, direction, priority, dest))

        return calls

    # ------------------------------------------------------------------
    # Scenario-driven generation (Phase 3)
    # ------------------------------------------------------------------
    def _generate_scenario_calls(
        self, sim_time: datetime, time_per_step: float, max_floor: int
    ) -> list[tuple[int, str, str, int]]:
        """Generate calls shaped by the active scenario profile."""
        sc = self.scenario
        assert sc is not None

        lam = sc["lambda_base"] / 60.0 * time_per_step
        num_calls = int(self.rng.poisson(lam))
        express_pct = sc.get("express_pct", 0.05)

        calls: list[tuple[int, str, str, int]] = []

        for _ in range(num_calls):
            priority = "EXPRESS" if self.rng.random() < express_pct else "NORMAL"

            if self.scenario_name == "morning_rush":
                calls.append(
                    self._morning_rush_call(max_floor, priority)
                )
            elif self.scenario_name == "lunch_peak":
                calls.append(
                    self._lunch_peak_call(max_floor, priority)
                )
            elif self.scenario_name == "evening_rush":
                calls.append(
                    self._evening_rush_call(max_floor, priority)
                )
            else:  # random_uniform
                calls.append(
                    self._random_uniform_call(max_floor, priority)
                )

        return calls

    # ------------------------------------------------------------------
    # Scenario-specific call generators
    # ------------------------------------------------------------------
    def _morning_rush_call(
        self, max_floor: int, priority: str
    ) -> tuple[int, str, str, int]:
        """80 % of calls are UP from floor 1 to a random higher floor."""
        if self.rng.random() < 0.80:
            floor = 1
            dest = int(self.rng.integers(2, max_floor + 1))
            return (floor, "UP", priority, dest)
        else:
            # Remaining 20 % are random
            return self._random_uniform_call(max_floor, priority)

    def _lunch_peak_call(
        self, max_floor: int, priority: str
    ) -> tuple[int, str, str, int]:
        """50/50 UP and DOWN, mid-floors are more active."""
        # Bias toward mid-floors (triangular distribution)
        mid = max_floor // 2
        floor = int(
            np.clip(
                self.rng.triangular(1, mid, max_floor),
                1,
                max_floor,
            )
        )
        dest = floor
        while dest == floor:
            dest = int(
                np.clip(
                    self.rng.triangular(1, mid, max_floor),
                    1,
                    max_floor,
                )
            )
        direction = "UP" if dest > floor else "DOWN"
        return (floor, direction, priority, dest)

    def _evening_rush_call(
        self, max_floor: int, priority: str
    ) -> tuple[int, str, str, int]:
        """80 % of calls are DOWN from an upper floor to floor 1."""
        if self.rng.random() < 0.80:
            floor = int(self.rng.integers(2, max_floor + 1))
            dest = 1
            return (floor, "DOWN", priority, dest)
        else:
            return self._random_uniform_call(max_floor, priority)

    def _random_uniform_call(
        self, max_floor: int, priority: str
    ) -> tuple[int, str, str, int]:
        """Uniform random origin and destination."""
        floor = int(self.rng.integers(1, max_floor + 1))
        dest = floor
        while dest == floor:
            dest = int(self.rng.integers(1, max_floor + 1))
        direction = "UP" if dest > floor else "DOWN"
        return (floor, direction, priority, dest)


def get_scenario_names() -> list[str]:
    """Return all available scenario names."""
    return list(SCENARIOS.keys())


def get_scenario_info(name: str) -> dict:
    """Return the profile dict for a named scenario."""
    return SCENARIOS[name]
