"""Dispatch package — elevator assignment strategies."""

from backend.dispatch.base import DispatchStrategy
from backend.dispatch.gbfs import GBFSDispatcher
from backend.dispatch.nearest import NearestLiftDispatcher
from backend.dispatch.round_robin import RoundRobinDispatcher
from backend.dispatch.scan import SCANDispatcher

__all__ = [
    "DispatchStrategy",
    "GBFSDispatcher",
    "NearestLiftDispatcher",
    "RoundRobinDispatcher",
    "SCANDispatcher",
]

# Registry for easy lookup by name
STRATEGY_REGISTRY: dict[str, type[DispatchStrategy]] = {
    "gbfs": GBFSDispatcher,
    "nearest": NearestLiftDispatcher,
    "round_robin": RoundRobinDispatcher,
    "scan": SCANDispatcher,
}


def get_strategy(name: str, building) -> DispatchStrategy:
    """Instantiate a dispatch strategy by name."""
    cls = STRATEGY_REGISTRY.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown strategy '{name}'. "
            f"Choose from: {list(STRATEGY_REGISTRY.keys())}"
        )
    return cls(building)


def get_strategy_names() -> list[str]:
    """Return all available strategy names."""
    return list(STRATEGY_REGISTRY.keys())
