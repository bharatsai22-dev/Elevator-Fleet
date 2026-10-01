"""
Dynamic Weight Adjuster — SLA-driven GBFS weight recalibration.

Every 30 seconds (configurable), this module:
    1. Measures current building metrics (avg wait, load variance, traffic intensity).
    2. Compares metrics against SLA targets.
    3. Adjusts the GBFS weight vector accordingly.
    4. Clamps all weights to configured bounds and normalises to sum ≈ 1.0.

Adjustment rules:
    - SLA violation  → boost direction_bias, reduce distance weight
    - Load imbalance → boost load_balance weight
    - High traffic   → boost emergency_bonus
    - Low traffic    → boost distance weight (optimise energy)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.algorithms.gbfs_dispatcher import GBFSDispatcher
    from backend.simulation.models import Building


class DynamicWeightAdjuster:
    """Periodically recalibrates GBFS heuristic weights based on live metrics."""

    def __init__(
        self,
        gbfs: "GBFSDispatcher",
        building: "Building",
        sla_wait_target_sec: float = 45.0,
        adjustment_interval_sec: float = 30.0,
        load_variance_threshold: float = 0.25,
    ) -> None:
        self.gbfs = gbfs
        self.building = building

        # SLA configuration
        self.sla_wait_target_sec = sla_wait_target_sec
        self.sla_wait_warning_sec = sla_wait_target_sec + 10.0

        # Thresholds
        self.load_variance_threshold = load_variance_threshold
        self.adjustment_interval_sec = adjustment_interval_sec

        self.last_adjustment_time = datetime.now()
        self.adjustment_history: list[dict] = []

    # ------------------------------------------------------------------
    # Metric collection
    # ------------------------------------------------------------------
    def calculate_metrics(self) -> dict:
        """Snapshot of current building health metrics."""
        loads = [e.occupancy_percent() for e in self.building.elevators]
        n = len(loads)
        avg_load = sum(loads) / n if n else 0.0
        max_load = max(loads) if loads else 0.0
        min_load = min(loads) if loads else 0.0

        # Standard deviation of loads
        variance = (sum((l - avg_load) ** 2 for l in loads) / n) ** 0.5 if n else 0.0

        # Average wait from recent completed calls
        recent = self.building.completed_calls[-50:]
        avg_wait = (
            sum(c["wait_time"] for c in recent) / len(recent)
            if recent
            else 0.0
        )

        # Traffic intensity (calls in the last 100 history entries, rough calls/min)
        recent_calls = self.building.call_history[-100:]
        traffic_intensity = len(recent_calls) / 2.0  # approximation

        return {
            "avg_load": round(avg_load, 2),
            "max_load": round(max_load, 2),
            "min_load": round(min_load, 2),
            "load_variance": round(variance, 4),
            "avg_wait_time": round(avg_wait, 2),
            "traffic_intensity": round(traffic_intensity, 2),
        }

    # ------------------------------------------------------------------
    # Main adjustment logic
    # ------------------------------------------------------------------
    def adjust_weights(self, force: bool = False) -> dict:
        """
        Recalibrate GBFS weights if the cooldown has elapsed.

        Args:
            force: Skip cooldown check.

        Returns:
            The (possibly updated) weight dictionary.
        """
        now = datetime.now()
        elapsed = (now - self.last_adjustment_time).total_seconds()

        if not force and elapsed < self.adjustment_interval_sec:
            return self.gbfs.get_current_weights()

        self.last_adjustment_time = now
        metrics = self.calculate_metrics()
        new_weights = self.gbfs.get_current_weights()
        reasons: list[str] = []

        # ---- RULE 1: SLA violation ----
        if metrics["avg_wait_time"] > self.sla_wait_target_sec:
            reasons.append(
                f"SLA VIOLATION: wait={metrics['avg_wait_time']:.1f}s "
                f"> {self.sla_wait_target_sec}s"
            )
            new_weights["direction_bias"] += 0.05
            new_weights["distance"] -= 0.05
            new_weights["wait_time"] += 0.03

        # ---- RULE 2: Load imbalance ----
        if metrics["load_variance"] > self.load_variance_threshold:
            reasons.append(
                f"LOAD IMBALANCE: variance={metrics['load_variance']:.3f} "
                f"> {self.load_variance_threshold}"
            )
            new_weights["load_balance"] += 0.08
            new_weights["distance"] -= 0.05

        # ---- RULE 3: High traffic ----
        if metrics["traffic_intensity"] > 5.0:
            reasons.append(
                f"HIGH TRAFFIC: {metrics['traffic_intensity']:.1f} calls/min"
            )
            new_weights["direction_bias"] += 0.03
            new_weights["emergency_bonus"] += 0.02

        # ---- RULE 4: Low traffic ----
        if metrics["traffic_intensity"] < 1.0:
            reasons.append(
                f"LOW TRAFFIC: {metrics['traffic_intensity']:.1f} calls/min"
            )
            new_weights["distance"] += 0.05
            new_weights["direction_bias"] -= 0.02

        # Normalise to sum ≈ 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}

        # Apply and log
        self.gbfs.set_weights(new_weights)

        self.adjustment_history.append(
            {
                "timestamp": now.isoformat(),
                "metrics": metrics,
                "new_weights": {k: round(v, 4) for k, v in new_weights.items()},
                "reasons": reasons if reasons else ["Routine check — no changes"],
            }
        )

        return self.gbfs.get_current_weights()

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------
    def get_history(self, n: int = 20) -> list[dict]:
        """Return the last *n* adjustment records."""
        return self.adjustment_history[-n:]
