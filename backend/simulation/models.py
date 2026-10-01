"""
Core Data Models for the Enterprise Elevator Fleet Dispatcher.

Contains:
    - Passenger: Represents a person requesting an elevator.
    - Elevator:  Represents a single elevator car with direction-aware queues.
    - Building:  Represents the entire building with global call queues and SLA tracking.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Passenger
# ---------------------------------------------------------------------------
@dataclass
class Passenger:
    """A single passenger requesting elevator service."""

    passenger_id: str = field(default_factory=lambda: f"PAX_{uuid.uuid4().hex[:8]}")
    origin_floor: int = 1
    dest_floor: int = 1
    priority: str = "NORMAL"        # "NORMAL" or "EXPRESS"
    direction: str = "UP"           # "UP" or "DOWN"
    request_time: datetime = field(default_factory=datetime.now)
    pickup_time: Optional[datetime] = None
    dropoff_time: Optional[datetime] = None
    weight_kg: float = 75.0         # Average human weight

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------
    def waiting_time_sec(self) -> Optional[float]:
        """Seconds between requesting and being picked up."""
        if self.pickup_time is not None:
            return (self.pickup_time - self.request_time).total_seconds()
        return None

    def travel_time_sec(self) -> Optional[float]:
        """Seconds between pickup and drop-off."""
        if self.pickup_time is not None and self.dropoff_time is not None:
            return (self.dropoff_time - self.pickup_time).total_seconds()
        return None

    def total_time_sec(self) -> Optional[float]:
        """Total time from request to drop-off."""
        if self.dropoff_time is not None:
            return (self.dropoff_time - self.request_time).total_seconds()
        return None

    def __repr__(self) -> str:
        return (
            f"Passenger({self.passenger_id}, "
            f"{self.origin_floor}→{self.dest_floor}, "
            f"priority={self.priority})"
        )


# ---------------------------------------------------------------------------
# Elevator
# ---------------------------------------------------------------------------
@dataclass
class Elevator:
    """
    A single elevator car.

    Maintains three direction-aware queues:
        up_queue    – floors where passengers want to go UP
        down_queue  – floors where passengers want to go DOWN
        express_queue – emergency / high-priority pickup floors
    """

    elevator_id: int = 0
    current_floor: int = 1
    direction: str = "IDLE"          # "UP", "DOWN", "IDLE"
    passengers: list = field(default_factory=list)   # list[Passenger]

    # Direction-aware queues (floor numbers)
    up_queue: list = field(default_factory=list)
    down_queue: list = field(default_factory=list)
    express_queue: list = field(default_factory=list)

    # Physical constraints
    max_load_kg: float = 1000.0
    max_passengers: int = 10
    total_load_kg: float = 0.0

    # Power model
    power_consumption_w: float = 200.0    # Idle watts
    POWER_IDLE_W: float = 200.0
    POWER_MOVING_W: float = 5000.0

    # Operational state
    idle_time_sec: float = 0.0
    is_operational: bool = True

    # Telemetry counters
    trips_completed: int = 0
    total_passengers_served: int = 0
    total_distance_floors: int = 0

    # ------------------------------------------------------------------
    # Capacity helpers
    # ------------------------------------------------------------------
    def can_accept_passenger(self, passenger: Passenger) -> bool:
        """True if the elevator has enough weight AND headcount capacity."""
        return (
            self.is_operational
            and self.total_load_kg + passenger.weight_kg <= self.max_load_kg
            and len(self.passengers) < self.max_passengers
        )

    def occupancy_percent(self) -> float:
        """Current load as a percentage of maximum weight capacity."""
        return (self.total_load_kg / self.max_load_kg) * 100.0 if self.max_load_kg > 0 else 0.0

    # ------------------------------------------------------------------
    # Passenger management
    # ------------------------------------------------------------------
    def board_passenger(self, passenger: Passenger) -> bool:
        """Attempt to board a passenger.  Returns True on success."""
        if not self.can_accept_passenger(passenger):
            return False
        self.passengers.append(passenger)
        self.total_load_kg += passenger.weight_kg
        passenger.pickup_time = datetime.now()
        return True

    def alight_passenger(self, passenger: Passenger) -> None:
        """Remove a passenger who has reached their destination."""
        if passenger in self.passengers:
            self.passengers.remove(passenger)
            self.total_load_kg = max(0.0, self.total_load_kg - passenger.weight_kg)
            passenger.dropoff_time = datetime.now()
            self.trips_completed += 1
            self.total_passengers_served += 1

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------
    def add_to_queue(self, floor: int, direction: str) -> None:
        """Add a floor to the appropriate directional queue."""
        if direction == "UP":
            if floor not in self.up_queue:
                self.up_queue.append(floor)
        elif direction == "DOWN":
            if floor not in self.down_queue:
                self.down_queue.append(floor)

    def add_express_call(self, floor: int) -> None:
        """Add an emergency / high-priority floor."""
        if floor not in self.express_queue:
            self.express_queue.append(floor)

    def has_pending_stops(self) -> bool:
        """True if any queue still has work."""
        return bool(self.up_queue or self.down_queue or self.express_queue)

    def all_pending_floors(self) -> list:
        """Return a de-duplicated list of all floors this elevator must visit."""
        floors = set(self.up_queue) | set(self.down_queue) | set(self.express_queue)
        # Also include destination floors of on-board passengers
        for p in self.passengers:
            floors.add(p.dest_floor)
        return sorted(floors)

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------
    def move_one_floor(self, target_floor: int) -> None:
        """Move one floor closer to *target_floor* and update telemetry."""
        if target_floor > self.current_floor:
            self.current_floor += 1
            self.direction = "UP"
        elif target_floor < self.current_floor:
            self.current_floor -= 1
            self.direction = "DOWN"
        else:
            self.direction = "IDLE"

        self.total_distance_floors += 1
        self.idle_time_sec = 0.0
        self.power_consumption_w = self.POWER_MOVING_W

    def set_idle(self) -> None:
        """Mark this elevator as idle."""
        self.direction = "IDLE"
        self.power_consumption_w = self.POWER_IDLE_W

    def __repr__(self) -> str:
        return (
            f"Elevator(id={self.elevator_id}, "
            f"floor={self.current_floor}, "
            f"dir={self.direction}, "
            f"pax={len(self.passengers)}/{self.max_passengers}, "
            f"load={self.total_load_kg:.0f}/{self.max_load_kg:.0f}kg)"
        )


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------
@dataclass
class Building:
    """
    The entire building: floors, elevators, and global call management.

    Maintains three global call queues (direction-aware):
        up_calls      – (floor, timestamp)
        down_calls    – (floor, timestamp)
        express_calls – (floor, timestamp)
    """

    num_floors: int = 15
    elevators: list = field(default_factory=list)  # list[Elevator]

    # Global direction-aware call queues
    up_calls: list = field(default_factory=list)       # list[tuple[int, datetime]]
    down_calls: list = field(default_factory=list)     # list[tuple[int, datetime]]
    express_calls: list = field(default_factory=list)  # list[tuple[int, datetime]]

    # Traffic pattern context
    current_hour: int = 0

    # SLA tracking
    avg_wait_time_sec: float = 0.0
    max_wait_time_sec: float = 0.0

    # Full call history (used by predictor + weight adjuster)
    call_history: list = field(default_factory=list)
    completed_calls: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # Initialiser helper
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, num_floors: int = 15, num_elevators: int = 4) -> "Building":
        """Factory: create a building with *num_elevators* idle cars at floor 1."""
        elevators = [
            Elevator(elevator_id=i, current_floor=1)
            for i in range(num_elevators)
        ]
        return cls(num_floors=num_floors, elevators=elevators)

    # ------------------------------------------------------------------
    # Call registration
    # ------------------------------------------------------------------
    def add_call(
        self, floor: int, direction: str, priority: str = "NORMAL"
    ) -> str:
        """
        Register a new call.

        Returns:
            call_id (str): A unique identifier for this call.
        """
        call_id = f"CALL_{len(self.call_history)}_{datetime.now().timestamp():.0f}"
        now = datetime.now()

        if priority == "EXPRESS":
            self.express_calls.append((floor, now))
        elif direction == "UP":
            self.up_calls.append((floor, now))
        else:
            self.down_calls.append((floor, now))

        self.call_history.append(
            {
                "call_id": call_id,
                "floor": floor,
                "direction": direction,
                "priority": priority,
                "timestamp": now,
                "assigned_elevator": None,
                "pickup_time": None,
                "wait_time": None,
            }
        )
        return call_id

    def get_pending_calls(self) -> list:
        """Return (floor, direction, priority) for every pending call."""
        pending = []
        for floor, _ts in self.up_calls:
            pending.append((floor, "UP", "NORMAL"))
        for floor, _ts in self.down_calls:
            pending.append((floor, "DOWN", "NORMAL"))
        for floor, _ts in self.express_calls:
            pending.append((floor, "BOTH", "EXPRESS"))
        return pending

    def remove_call(self, floor: int, direction: str, priority: str = "NORMAL") -> None:
        """Remove the first matching call from the appropriate queue."""
        if priority == "EXPRESS":
            self.express_calls = [
                (f, ts) for f, ts in self.express_calls if f != floor
            ]
        elif direction == "UP":
            removed = False
            new_list = []
            for f, ts in self.up_calls:
                if f == floor and not removed:
                    removed = True
                    continue
                new_list.append((f, ts))
            self.up_calls = new_list
        else:
            removed = False
            new_list = []
            for f, ts in self.down_calls:
                if f == floor and not removed:
                    removed = True
                    continue
                new_list.append((f, ts))
            self.down_calls = new_list

    # ------------------------------------------------------------------
    # SLA helpers
    # ------------------------------------------------------------------
    def record_completion(self, passenger: Passenger) -> None:
        """Record a completed trip for SLA tracking."""
        wait = passenger.waiting_time_sec()
        if wait is not None:
            self.completed_calls.append(
                {
                    "passenger_id": passenger.passenger_id,
                    "wait_time": wait,
                    "travel_time": passenger.travel_time_sec(),
                    "timestamp": datetime.now(),
                }
            )
            # Rolling average
            n = len(self.completed_calls)
            self.avg_wait_time_sec = (
                (self.avg_wait_time_sec * (n - 1) + wait) / n
            )
            self.max_wait_time_sec = max(self.max_wait_time_sec, wait)

    def __repr__(self) -> str:
        return (
            f"Building(floors={self.num_floors}, "
            f"elevators={len(self.elevators)}, "
            f"pending_calls={len(self.get_pending_calls())})"
        )
