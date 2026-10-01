"""
Traffic Predictor — Exponential Smoothing Forecaster.

Predicts call arrival rates for the next 2-5 minutes using
exponential smoothing on observed call history.  The forecast
is fed back into the GBFS heuristic via the Dynamic Weight Adjuster.

Key features:
    - Pre-populated base arrival rates for a typical office building
    - Learns from live observations
    - Produces a 5-minute forecast with confidence level
    - Generates actionable recommendations
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.simulation.models import Building


class TrafficPredictor:
    """Exponential-smoothing traffic forecaster."""

    def __init__(
        self,
        building: "Building",
        smoothing_factor: float = 0.7,
    ) -> None:
        self.building = building
        self.smoothing_factor = smoothing_factor

        # Base arrival rates (calls/minute per floor, keyed by hour)
        self.base_arrival_rates: dict[int, float] = {
            0: 0.01, 1: 0.01, 2: 0.01, 3: 0.01, 4: 0.01, 5: 0.01,
            6: 0.20, 7: 0.80, 8: 2.50, 9: 2.00, 10: 1.20,
            11: 0.90, 12: 1.80, 13: 1.50, 14: 1.00, 15: 0.70,
            16: 0.80, 17: 1.20, 18: 0.50, 19: 0.30, 20: 0.20,
            21: 0.10, 22: 0.05, 23: 0.02,
        }

        self.predicted_rates: dict[int, float] = dict(self.base_arrival_rates)
        self.observation_history: list[tuple[int, int, datetime]] = []

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------
    def observe_call(self, floor: int, timestamp: datetime) -> None:
        """Record a single call observation."""
        self.observation_history.append((timestamp.hour, floor, timestamp))

    # ------------------------------------------------------------------
    # Exponential smoothing update
    # ------------------------------------------------------------------
    def update_prediction(self) -> None:
        """
        Update predicted arrival rates based on recent observations.

        predicted(t+1) = α × observed(t) + (1 − α) × predicted(t)
        """
        cutoff = datetime.now() - timedelta(hours=1)
        for hour in range(24):
            recent = [
                o for o in self.observation_history
                if o[0] == hour and o[2] > cutoff
            ]
            observed_rate = len(recent) / 60.0  # calls per minute
            current_pred = self.predicted_rates.get(hour, 0.5)
            self.predicted_rates[hour] = (
                self.smoothing_factor * observed_rate
                + (1 - self.smoothing_factor) * current_pred
            )

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------
    def forecast_next_n_minutes(self, n_minutes: int = 5) -> dict:
        """
        Forecast call volume for the next *n_minutes*.

        Returns:
            dict with forecasted_volume, confidence, peak_floor_range,
            recommendation.
        """
        now = datetime.now()
        total_forecast = 0.0
        for i in range(n_minutes):
            future = now + timedelta(minutes=i)
            rate = self.predicted_rates.get(future.hour, 0.5)
            total_forecast += rate

        # Confidence increases with observation count (max 1.0)
        confidence = min(len(self.observation_history) / 500.0, 1.0)

        # Peak floor range (heuristic default)
        peak_low, peak_high = 3, 12

        # Actionable recommendation
        if total_forecast > 3.0:
            recommendation = (
                "HIGH TRAFFIC EXPECTED: Boost direction_bias, monitor SLA"
            )
        elif total_forecast > 1.0:
            recommendation = "NORMAL TRAFFIC: Standard dispatch"
        else:
            recommendation = "LOW TRAFFIC: Optimise for distance efficiency"

        return {
            "forecasted_volume": int(total_forecast),
            "confidence": round(confidence, 3),
            "peak_floor_range": (peak_low, peak_high),
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------
    def get_current_rates(self) -> dict[int, float]:
        """Return the current predicted arrival-rate table."""
        return {h: round(r, 4) for h, r in self.predicted_rates.items()}
