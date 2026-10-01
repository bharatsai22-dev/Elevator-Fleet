"""
Telemetry Logger — CSV Data Generator for ML Training.

Logs every call assignment and completion to `elevator_training_data.csv`
with 21 columns, using buffered batch writes for performance.

Output is a 100 % plagiarism-free synthetic dataset suitable for
Scikit-Learn Random Forest or Gradient Boosting training.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.simulation.models import Building, Passenger


FIELDNAMES = [
    "timestamp",
    "call_id",
    "origin_floor",
    "dest_floor",
    "call_priority",
    "assigned_elevator_id",
    "pickup_time_actual_sec",
    "dropoff_time_sec",
    "elevator_load_kg_at_pickup",
    "wait_time_sec",
    "travel_time_sec",
    "direction_match",
    "traffic_intensity",
    "hour_of_day",
    "gbfs_score",
    "astar_cost",
    "direction_weight",
    "load_weight",
    "distance_weight",
    "wait_weight",
    "reopt_triggered",
    "reopt_count",
]


class TelemetryLogger:
    """Buffered CSV logger for elevator simulation telemetry."""

    def __init__(
        self,
        csv_filename: str = "elevator_training_data.csv",
        buffer_size: int = 100,
    ) -> None:
        self.csv_filename = csv_filename
        self.buffer: list[dict] = []
        self.buffer_size = buffer_size
        self.total_rows_written: int = 0

        # Write header (overwrite on fresh start)
        try:
            with open(self.csv_filename, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
                writer.writeheader()
        except OSError as exc:
            print(f"[TelemetryLogger] WARNING: Could not initialise CSV: {exc}")

    # ------------------------------------------------------------------
    # Assignment logging
    # ------------------------------------------------------------------
    def log_call_assignment(
        self,
        call_id: str,
        passenger: "Passenger",
        elevator_id: int,
        gbfs_score: float,
        weights: dict,
        traffic_intensity: float,
        elevator_load_kg: float = 0.0,
    ) -> None:
        """Log the moment GBFS assigns a call to an elevator."""
        row = {
            "timestamp": datetime.now().isoformat(),
            "call_id": call_id,
            "origin_floor": passenger.origin_floor,
            "dest_floor": passenger.dest_floor,
            "call_priority": passenger.priority,
            "assigned_elevator_id": elevator_id,
            "pickup_time_actual_sec": None,
            "dropoff_time_sec": None,
            "elevator_load_kg_at_pickup": round(elevator_load_kg, 1),
            "wait_time_sec": None,
            "travel_time_sec": None,
            "direction_match": 1.0 if passenger.direction == "UP" else 0.0,
            "traffic_intensity": round(traffic_intensity, 2),
            "hour_of_day": datetime.now().hour,
            "gbfs_score": round(gbfs_score, 4),
            "astar_cost": None,
            "direction_weight": round(weights.get("direction_bias", 0), 4),
            "load_weight": round(weights.get("load_balance", 0), 4),
            "distance_weight": round(weights.get("distance", 0), 4),
            "wait_weight": round(weights.get("wait_time", 0), 4),
            "reopt_triggered": 0,
            "reopt_count": 0,
        }
        self._append(row)

    # ------------------------------------------------------------------
    # Completion logging
    # ------------------------------------------------------------------
    def log_call_completion(
        self,
        call_id: str,
        passenger: "Passenger",
        elevator_id: int,
        astar_cost: float,
        reopt_count: int,
        traffic_intensity: float = 0.0,
    ) -> None:
        """Log the moment a passenger is dropped off."""
        wait = passenger.waiting_time_sec() or 0.0
        travel = passenger.travel_time_sec() or 0.0

        row = {
            "timestamp": datetime.now().isoformat(),
            "call_id": call_id,
            "origin_floor": passenger.origin_floor,
            "dest_floor": passenger.dest_floor,
            "call_priority": passenger.priority,
            "assigned_elevator_id": elevator_id,
            "pickup_time_actual_sec": round(wait, 2),
            "dropoff_time_sec": round(
                passenger.dropoff_time.timestamp(), 2
            )
            if passenger.dropoff_time
            else None,
            "elevator_load_kg_at_pickup": None,
            "wait_time_sec": round(wait, 2),
            "travel_time_sec": round(travel, 2),
            "direction_match": 1.0 if passenger.direction == "UP" else 0.0,
            "traffic_intensity": round(traffic_intensity, 2),
            "hour_of_day": datetime.now().hour,
            "gbfs_score": None,
            "astar_cost": round(astar_cost, 2),
            "direction_weight": None,
            "load_weight": None,
            "distance_weight": None,
            "wait_weight": None,
            "reopt_triggered": 1 if reopt_count > 0 else 0,
            "reopt_count": reopt_count,
        }
        self._append(row)

    # ------------------------------------------------------------------
    # Buffer management
    # ------------------------------------------------------------------
    def _append(self, row: dict) -> None:
        self.buffer.append(row)
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        """Write the in-memory buffer to the CSV file."""
        if not self.buffer:
            return
        try:
            with open(
                self.csv_filename, "a", newline="", encoding="utf-8"
            ) as fh:
                writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
                writer.writerows(self.buffer)
            self.total_rows_written += len(self.buffer)
            self.buffer.clear()
        except OSError as exc:
            print(f"[TelemetryLogger] ERROR writing CSV: {exc}")

    def close(self) -> None:
        """Flush remaining buffer."""
        self.flush()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        return {
            "csv_file": self.csv_filename,
            "rows_written": self.total_rows_written,
            "rows_buffered": len(self.buffer),
            "columns": len(FIELDNAMES),
        }
