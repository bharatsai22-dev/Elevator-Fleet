"""
Metrics Collector — centralised simulation metrics and reporting.

Tracks call counts, wait times, distance, capacity rejections,
and A* re-optimisations.  Supports dict-style access for backward
compatibility with the Pygame visualizer.
"""

from __future__ import annotations


class MetricsCollector:
    """Collects and reports simulation metrics."""

    def __init__(self) -> None:
        self.total_calls: int = 0
        self.total_completed: int = 0
        self.total_wait_time: float = 0.0
        self.max_wait_time: float = 0.0
        self.total_distance: int = 0
        self.emergency_calls: int = 0
        self.capacity_rejections: int = 0
        self.reopt_count: int = 0

    # ------------------------------------------------------------------
    # Dict-style access (backward compat with visualization.py)
    # ------------------------------------------------------------------
    def __getitem__(self, key: str):
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        setattr(self, key, value)

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------
    def record_call(self, priority: str) -> None:
        """Record a new incoming call."""
        self.total_calls += 1
        if priority == "EXPRESS":
            self.emergency_calls += 1

    def record_completion(self, wait_time: float) -> None:
        """Record a completed passenger trip."""
        self.total_completed += 1
        self.total_wait_time += wait_time
        self.max_wait_time = max(self.max_wait_time, wait_time)

    def record_rejection(self) -> None:
        """Record a capacity rejection."""
        self.capacity_rejections += 1

    def record_reopt(self) -> None:
        """Record an accepted A* re-optimisation."""
        self.reopt_count += 1

    def record_distance(self, floors: int = 1) -> None:
        """Record floors travelled."""
        self.total_distance += floors

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------
    @property
    def avg_wait_time(self) -> float:
        """Average wait time across all completed trips."""
        if self.total_completed > 0:
            return self.total_wait_time / self.total_completed
        return 0.0

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def print_progress(self, current_step: int, total_steps: int) -> None:
        """Print a single-line progress report."""
        avg_wait = self.avg_wait_time
        print(
            f"  Step {current_step:>5}/{total_steps} | "
            f"Calls={self.total_calls:>4} | "
            f"Completed={self.total_completed:>4} | "
            f"AvgWait={avg_wait:>5.1f}s | "
            f"MaxWait={self.max_wait_time:>5.1f}s | "
            f"Distance={self.total_distance:>5} floors"
        )

    def generate_summary(
        self,
        total_steps: int,
        time_per_step: float,
        sla_target: float,
        csv_rows: int,
    ) -> dict:
        """Generate the final simulation summary dictionary."""
        avg_wait = self.avg_wait_time
        return {
            "total_duration_sec": total_steps * time_per_step,
            "total_calls_generated": self.total_calls,
            "total_completed": self.total_completed,
            "emergency_calls": self.emergency_calls,
            "capacity_rejections": self.capacity_rejections,
            "avg_wait_time_sec": round(avg_wait, 2),
            "max_wait_time_sec": round(self.max_wait_time, 2),
            "total_distance_floors": self.total_distance,
            "total_reoptimisations": self.reopt_count,
            "sla_target_sec": sla_target,
            "sla_met": avg_wait <= sla_target,
            "csv_rows_written": csv_rows,
        }

    @staticmethod
    def print_summary(s: dict) -> None:
        """Print the formatted simulation summary."""
        print()
        print("=" * 65)
        print("  SIMULATION SUMMARY")
        print("=" * 65)
        for key, value in s.items():
            label = key.replace("_", " ").title()
            if isinstance(value, float):
                print(f"  {label:<30}: {value:>10.2f}")
            elif isinstance(value, bool):
                print(f"  {label:<30}: {'YES' if value else 'NO':>10}")
            else:
                print(f"  {label:<30}: {value!s:>10}")
        print("=" * 65)
        print(
            f"\n  CSV Output: elevator_training_data.csv"
            f" -> {s['csv_rows_written']} rows x 21 columns"
        )
        print(
            "  Ready for ML training"
            " (Scikit-Learn RandomForest on gbfs_score vs wait_time)"
        )
        print()
