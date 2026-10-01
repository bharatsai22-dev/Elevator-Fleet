"""
Abstract base class for elevator dispatch strategies.

Every dispatch strategy (GBFS, nearest-lift, round-robin, SCAN)
implements this interface so they can be swapped interchangeably
during benchmarks and the live dashboard.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.simulator.models import Building


class DispatchStrategy(ABC):
    """Base class for all elevator dispatch strategies."""

    def __init__(self, building: "Building") -> None:
        self.building = building

    @abstractmethod
    def assign_elevator(
        self,
        floor: int,
        direction: str,
        priority: str = "NORMAL",
    ) -> tuple[int, float, dict]:
        """
        Assign the best elevator to a call.

        Args:
            floor:     The floor the call originates from.
            direction: "UP" or "DOWN".
            priority:  "NORMAL" or "EXPRESS".

        Returns:
            (elevator_id, estimated_wait_sec, decision_details)
        """
        ...

    def get_name(self) -> str:
        """Return a human-readable name for this strategy."""
        return self.__class__.__name__
