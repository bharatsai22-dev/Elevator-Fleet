"""
Enterprise Elevator Fleet Simulator — CLI Entry Point.

Usage:
    python -m backend.main                 # uses config.json
    python -m backend.main config.json     # custom config
    python -m backend.main --visualize     # with Pygame visualizer
"""

from __future__ import annotations

import json
import os
import sys

# ---------------------------------------------------------------------------
# Resolve imports — works whether run as `python -m backend.main` from the
# project root **or** `python backend/main.py`
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.simulator.engine import SimulationEngine


# ═══════════════════════════════════════════════════════════════════════════
# Interactive input helpers
# ═══════════════════════════════════════════════════════════════════════════
def _prompt_int(label: str, default: int, min_val: int = 1) -> int:
    """Prompt the user for an integer value, showing the default."""
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            val = int(raw)
            if val < min_val:
                print(f"    [!]  Must be at least {min_val}. Try again.")
                continue
            return val
        except ValueError:
            print("    [!]  Please enter a valid number. Try again.")


def _prompt_float(label: str, default: float, min_val: float = 0.1) -> float:
    """Prompt the user for a float value, showing the default."""
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            val = float(raw)
            if val < min_val:
                print(f"    [!]  Must be at least {min_val}. Try again.")
                continue
            return val
        except ValueError:
            print("    [!]  Please enter a valid number. Try again.")


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # --- Parse --visualize flag ---
    _use_viz = "--visualize" in sys.argv
    _args = [a for a in sys.argv[1:] if a != "--visualize"]

    config_file = _args[0] if _args else os.path.join(
        _project_root, "config.json"
    )

    # Load base config
    with open(config_file, encoding="utf-8") as _fh:
        _base_config = json.load(_fh)

    # --- Interactive parameter input ---
    print()
    print("=" * 65)
    print("  ENTERPRISE ELEVATOR FLEET DISPATCHER -- CONFIGURATION")
    print("=" * 65)
    print("  Enter your simulation parameters below.")
    print("  Press ENTER to accept the default value shown in [brackets].")
    print("-" * 65)

    num_floors = _prompt_int(
        "Number of floors in the building",
        _base_config["simulation"]["building_floors"],
        min_val=2,
    )
    num_elevators = _prompt_int(
        "Number of elevators",
        _base_config["elevators"]["count"],
        min_val=1,
    )
    max_passengers = _prompt_int(
        "Max passengers per elevator",
        _base_config["elevators"]["max_passengers"],
        min_val=1,
    )
    duration_steps = _prompt_int(
        "Simulation duration (seconds)",
        _base_config["simulation"]["duration_steps"],
        min_val=10,
    )
    sla_target = _prompt_float(
        "SLA wait-time target (seconds)",
        _base_config["tuning"]["sla_wait_target_sec"],
        min_val=1.0,
    )

    scenario_case = _prompt_int(
        "Select Scenario (1: GBFS Auto-Dispatch, 2: Manual Elevator Selection)",
        1,
        min_val=1,
    )

    manual_mode_input = input("  Manual passenger mode (y/N) [N]: ").strip().lower()
    manual_mode = manual_mode_input == "y"

    seed = _prompt_int(
        "Random seed (for reproducibility)",
        _base_config.get("seed", 42),
        min_val=0,
    )

    # --- Apply user inputs to config ---
    _base_config["simulation"]["building_floors"] = num_floors
    _base_config["elevators"]["count"] = num_elevators
    _base_config["elevators"]["max_passengers"] = max_passengers
    _base_config["simulation"]["duration_steps"] = duration_steps
    _base_config["tuning"]["sla_wait_target_sec"] = sla_target
    _base_config["simulation"]["manual_mode"] = manual_mode
    _base_config["simulation"]["scenario_case"] = scenario_case
    _base_config["seed"] = seed

    # Write the updated config to a temporary file so the simulator reads it
    _temp_config_path = os.path.join(_project_root, "data", "_runtime_config.json")
    os.makedirs(os.path.dirname(_temp_config_path), exist_ok=True)
    with open(_temp_config_path, "w", encoding="utf-8") as _fh:
        json.dump(_base_config, _fh, indent=2)

    print("-" * 65)
    mode_label = "VISUAL" if _use_viz else "HEADLESS"
    print(f"  [OK] Configuration ready: {num_floors} floors, "
          f"{num_elevators} elevators, {duration_steps}s duration")
    print(f"  [OK] Seed: {seed}  |  Mode: {mode_label}")
    print("=" * 65)
    print()

    # --- Run ---
    simulator = SimulationEngine(_temp_config_path)

    if _use_viz:
        from backend.visualization import ElevatorVisualizer

        viz = ElevatorVisualizer(simulator)
        viz.run()
    else:
        simulator.run_simulation()
