"""Scenarios package — traffic generation profiles."""

from backend.scenarios.traffic import (
    TrafficGenerator,
    get_scenario_names,
    get_scenario_info,
    SCENARIOS,
)

__all__ = [
    "TrafficGenerator",
    "get_scenario_names",
    "get_scenario_info",
    "SCENARIOS",
]
