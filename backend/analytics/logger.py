"""
Telemetry Logger — CSV-based simulation data recording.

Writes a row to the training CSV for every call assignment and
completion event.  The resulting CSV can be used for:
    - Post-hoc analysis and visualisation
    - ML training (RandomForest on gbfs_score → predicted wait_time)
"""

from __future__ import annotations

import csv
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.simulator.models import Passenger


# CSV column schema
_FIELDNAMES = [
    "event_type",
    "call_id",
    "origin_floor",
    "dest_floor",
    "direction",
    "priority",
    "elevator_id",
    "gbfs_score",
    "weight_direction_bias",
    "weight_load_balance",
    "weight_distance",
    "weight_wait_time",
    "weight_emergency_bonus",
    "weight_fairness",
    "traffic_intensity",
    "elevator_load_kg",
    "wait_time_sec",
    "travel_time_sec",
    "total_time_sec",
    "astar_cost",
    "reopt_count",
]


class TelemetryLogger:
    """Writes simulation telemetry to a CSV file."""

    def __init__(self, csv_filename: str = "elevator_training_data.csv") -> None:
        self.csv_filename = csv_filename
        self.total_rows_written: int = 0

        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_filename) or ".", exist_ok=True)

        self._file = open(csv_filename, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=_FIELDNAMES)
        self._writer.writeheader()

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def log_call_assignment(
        self,
        call_id: str,
        passenger: "Passenger",
        elevator_id: int,
        gbfs_score: float,
        weights: dict,
        traffic_intensity: int,
        elevator_load_kg: float,
    ) -> None:
        """Record an elevator assignment event."""
        row = {
            "event_type": "ASSIGNMENT",
            "call_id": call_id,
            "origin_floor": passenger.origin_floor,
            "dest_floor": passenger.dest_floor,
            "direction": passenger.direction,
            "priority": passenger.priority,
            "elevator_id": elevator_id,
            "gbfs_score": round(gbfs_score, 4),
            "weight_direction_bias": round(weights.get("direction_bias", 0), 4),
            "weight_load_balance": round(weights.get("load_balance", 0), 4),
            "weight_distance": round(weights.get("distance", 0), 4),
            "weight_wait_time": round(weights.get("wait_time", 0), 4),
            "weight_emergency_bonus": round(weights.get("emergency_bonus", 0), 4),
            "weight_fairness": round(weights.get("fairness", 0), 4),
            "traffic_intensity": traffic_intensity,
            "elevator_load_kg": round(elevator_load_kg, 1),
            "wait_time_sec": "",
            "travel_time_sec": "",
            "total_time_sec": "",
            "astar_cost": "",
            "reopt_count": "",
        }
        self._writer.writerow(row)
        self.total_rows_written += 1

    def log_call_completion(
        self,
        call_id: str,
        passenger: "Passenger",
        elevator_id: int,
        astar_cost: float,
        reopt_count: int,
        traffic_intensity: int,
    ) -> None:
        """Record a call completion event."""
        row = {
            "event_type": "COMPLETION",
            "call_id": call_id,
            "origin_floor": passenger.origin_floor,
            "dest_floor": passenger.dest_floor,
            "direction": passenger.direction,
            "priority": passenger.priority,
            "elevator_id": elevator_id,
            "gbfs_score": "",
            "weight_direction_bias": "",
            "weight_load_balance": "",
            "weight_distance": "",
            "weight_wait_time": "",
            "weight_emergency_bonus": "",
            "weight_fairness": "",
            "traffic_intensity": traffic_intensity,
            "elevator_load_kg": "",
            "wait_time_sec": round(passenger.waiting_time_sec() or 0, 2),
            "travel_time_sec": round(passenger.travel_time_sec() or 0, 2),
            "total_time_sec": round(passenger.total_time_sec() or 0, 2),
            "astar_cost": round(astar_cost, 2),
            "reopt_count": reopt_count,
        }
        self._writer.writerow(row)
        self.total_rows_written += 1

    # ------------------------------------------------------------------
    # Legacy compatibility
    # ------------------------------------------------------------------
    def log_event(self, **kwargs) -> None:
        """Generic event logger for backward compatibility."""
        row = {k: kwargs.get(k, "") for k in _FIELDNAMES}
        row["event_type"] = kwargs.get("event_type", "GENERIC")
        self._writer.writerow(row)
        self.total_rows_written += 1

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Flush and close the CSV file."""
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()

    def __del__(self) -> None:
        self.close()
