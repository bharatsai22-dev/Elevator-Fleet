"""
Traffic Generator — Poisson-distributed call generation.

Generates elevator calls based on configurable traffic patterns
(morning rush, lunch peak, evening rush, etc.) with support for
a seeded RNG for reproducible benchmark runs.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from backend.simulator.models import Building


class TrafficGenerator:
    """Generates elevator calls based on traffic patterns and Poisson arrivals."""

    def __init__(
        self,
        building: "Building",
        config: dict,
        rng: np.random.Generator,
    ) -> None:
        self.building = building
        self.config = config
        self.rng = rng

    # ------------------------------------------------------------------
    # Traffic intensity
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

        hour = sim_time.hour
        lam = 2.0 * self._get_lambda_multiplier(hour) / 60.0 * time_per_step
        num_calls = int(self.rng.poisson(lam))

        calls: list[tuple[int, str, str, int]] = []
        max_floor = self.config["simulation"]["building_floors"]

        for _ in range(num_calls):
            floor = int(self.rng.integers(1, max_floor + 1))
            dest = floor
            while dest == floor:
                dest = int(self.rng.integers(1, max_floor + 1))

            direction = "UP" if dest > floor else "DOWN"
            priority = "EXPRESS" if self.rng.random() < 0.05 else "NORMAL"
            calls.append((floor, direction, priority, dest))

        return calls
