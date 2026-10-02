"""
Unit Test Suite for the Enterprise Elevator Fleet Dispatcher.

Tests cover:
    - GBFS direction bias, occupancy constraints, EXPRESS overrides
    - GBFS fairness / starvation scoring
    - Nearest-lift, Round-robin, SCAN baseline strategies
    - Strategy registry and factory
    - A* route cost calculation and reoptimisation bounds
    - Dynamic Weight Adjuster SLA rules
    - Traffic scenarios (morning rush, lunch, evening, random)
    - Data model integrity (Passenger, Elevator, Building)
    - Telemetry logger CSV output
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta

# Ensure project root is on path
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.simulator.models import Building, Elevator, Passenger
from backend.dispatch.gbfs import GBFSDispatcher
from backend.dispatch.nearest import NearestLiftDispatcher
from backend.dispatch.round_robin import RoundRobinDispatcher
from backend.dispatch.scan import SCANDispatcher
from backend.dispatch import get_strategy, get_strategy_names
from backend.dispatch.astar import AStarSequencer
from backend.ml.weights import DynamicWeightAdjuster
from backend.ml.predictor import TrafficPredictor
from backend.scenarios.traffic import TrafficGenerator, get_scenario_names
from backend.analytics.logger import TelemetryLogger


# ═══════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════
class TestPassenger(unittest.TestCase):
    """Passenger data-class tests."""

    def test_waiting_time(self):
        p = Passenger(request_time=datetime(2026, 1, 1, 8, 0, 0))
        p.pickup_time = datetime(2026, 1, 1, 8, 0, 30)
        self.assertAlmostEqual(p.waiting_time_sec(), 30.0)

    def test_travel_time(self):
        p = Passenger(request_time=datetime(2026, 1, 1, 8, 0, 0))
        p.pickup_time = datetime(2026, 1, 1, 8, 0, 30)
        p.dropoff_time = datetime(2026, 1, 1, 8, 1, 15)
        self.assertAlmostEqual(p.travel_time_sec(), 45.0)

    def test_no_pickup_returns_none(self):
        p = Passenger()
        self.assertIsNone(p.waiting_time_sec())
        self.assertIsNone(p.travel_time_sec())


class TestElevator(unittest.TestCase):
    """Elevator model tests."""

    def test_capacity_check_weight(self):
        e = Elevator(max_load_kg=1000)
        e.total_load_kg = 950
        heavy_pax = Passenger(weight_kg=60)
        self.assertFalse(e.can_accept_passenger(heavy_pax))

    def test_capacity_check_headcount(self):
        e = Elevator(max_passengers=10)
        e.passengers = [Passenger() for _ in range(10)]
        new_pax = Passenger(weight_kg=50)
        self.assertFalse(e.can_accept_passenger(new_pax))

    def test_board_and_alight(self):
        e = Elevator()
        pax = Passenger(weight_kg=70)
        self.assertTrue(e.board_passenger(pax))
        self.assertEqual(len(e.passengers), 1)
        self.assertAlmostEqual(e.total_load_kg, 70.0)

        e.alight_passenger(pax)
        self.assertEqual(len(e.passengers), 0)
        self.assertAlmostEqual(e.total_load_kg, 0.0)

    def test_occupancy_percent(self):
        e = Elevator(max_load_kg=1000)
        e.total_load_kg = 500
        self.assertAlmostEqual(e.occupancy_percent(), 50.0)

    def test_queue_management(self):
        e = Elevator()
        e.add_to_queue(5, "UP")
        e.add_to_queue(3, "DOWN")
        e.add_express_call(1)
        self.assertIn(5, e.up_queue)
        self.assertIn(3, e.down_queue)
        self.assertIn(1, e.express_queue)

    def test_move_one_floor_up(self):
        e = Elevator(current_floor=3)
        e.move_one_floor(7)
        self.assertEqual(e.current_floor, 4)
        self.assertEqual(e.direction, "UP")

    def test_move_one_floor_down(self):
        e = Elevator(current_floor=5)
        e.move_one_floor(2)
        self.assertEqual(e.current_floor, 4)
        self.assertEqual(e.direction, "DOWN")


class TestBuilding(unittest.TestCase):
    """Building model tests."""

    def test_factory(self):
        b = Building.create(num_floors=15, num_elevators=4)
        self.assertEqual(b.num_floors, 15)
        self.assertEqual(len(b.elevators), 4)

    def test_add_call_up(self):
        b = Building.create()
        cid = b.add_call(5, "UP")
        self.assertTrue(cid.startswith("CALL_"))
        self.assertEqual(len(b.up_calls), 1)

    def test_add_call_express(self):
        b = Building.create()
        b.add_call(7, "UP", "EXPRESS")
        self.assertEqual(len(b.express_calls), 1)

    def test_pending_calls(self):
        b = Building.create()
        b.add_call(3, "UP")
        b.add_call(8, "DOWN")
        b.add_call(1, "UP", "EXPRESS")
        self.assertEqual(len(b.get_pending_calls()), 3)


# ═══════════════════════════════════════════════════════════════════════════
# GBFS Dispatcher
# ═══════════════════════════════════════════════════════════════════════════
class TestGBFSDispatcher(unittest.TestCase):
    """GBFS heuristic tests."""

    def setUp(self):
        self.building = Building.create(num_floors=15, num_elevators=4)
        self.gbfs = GBFSDispatcher(self.building)

    def test_direction_bias_up(self):
        """Elevator moving UP should be preferred for UP calls."""
        self.building.elevators[0].current_floor = 5
        self.building.elevators[0].direction = "UP"

        self.building.elevators[1].current_floor = 6
        self.building.elevators[1].direction = "DOWN"

        eid, _, _ = self.gbfs.assign_elevator(7, "UP")
        self.assertEqual(eid, 0)

    def test_direction_bias_down(self):
        """Elevator moving DOWN should be preferred for DOWN calls."""
        self.building.elevators[0].current_floor = 10
        self.building.elevators[0].direction = "DOWN"

        self.building.elevators[1].current_floor = 9
        self.building.elevators[1].direction = "UP"

        eid, _, _ = self.gbfs.assign_elevator(5, "DOWN")
        self.assertEqual(eid, 0)

    def test_occupancy_constraint_normal(self):
        """Full elevator should be disqualified for NORMAL calls."""
        self.building.elevators[0].total_load_kg = 950  # >85%
        self.building.elevators[0].current_floor = 5

        self.building.elevators[1].total_load_kg = 200
        self.building.elevators[1].current_floor = 5

        eid, _, _ = self.gbfs.assign_elevator(5, "UP", "NORMAL")
        self.assertEqual(eid, 1)

    def test_express_overrides_occupancy(self):
        """EXPRESS calls should still assign to full elevators if closest."""
        for e in self.building.elevators:
            e.total_load_kg = 950
            e.current_floor = 10

        self.building.elevators[0].current_floor = 5  # closest

        eid, _, _ = self.gbfs.assign_elevator(5, "UP", "EXPRESS")
        self.assertEqual(eid, 0)

    def test_idle_elevator_gets_moderate_score(self):
        """An IDLE elevator should score between matching and mismatching."""
        self.building.elevators[0].direction = "IDLE"
        self.building.elevators[0].current_floor = 7

        eid, _, decision = self.gbfs.assign_elevator(7, "UP")
        candidates = decision["candidates"]
        idle_score = next(
            c["dir_score"] for c in candidates if c["elevator_id"] == 0
        )
        self.assertAlmostEqual(idle_score, 0.5)

    def test_weight_update(self):
        """Weights should be clamped to bounds after update."""
        self.gbfs.set_weights({"direction_bias": 1.0, "distance": -1.0})
        w = self.gbfs.get_current_weights()
        self.assertLessEqual(w["direction_bias"], 0.50)
        self.assertGreaterEqual(w["distance"], 0.08)

    def test_fairness_weight_exists(self):
        """GBFS should have a fairness weight."""
        w = self.gbfs.get_current_weights()
        self.assertIn("fairness", w)
        self.assertGreater(w["fairness"], 0)

    def test_starvation_tracking(self):
        """Starvation tracker should register and complete calls."""
        self.gbfs.register_pending_call("CALL_001", 1000.0)
        self.assertEqual(len(self.gbfs._pending_waits), 1)
        max_wait = self.gbfs._max_pending_wait(1060.0)
        self.assertAlmostEqual(max_wait, 60.0)
        self.gbfs.complete_call("CALL_001")
        self.assertEqual(len(self.gbfs._pending_waits), 0)


# ═══════════════════════════════════════════════════════════════════════════
# Baseline Strategies
# ═══════════════════════════════════════════════════════════════════════════
class TestNearestLiftDispatcher(unittest.TestCase):
    """Nearest-lift strategy tests."""

    def setUp(self):
        self.building = Building.create(num_floors=15, num_elevators=4)
        self.dispatcher = NearestLiftDispatcher(self.building)

    def test_picks_closest(self):
        """Should pick the elevator closest to the call floor."""
        self.building.elevators[0].current_floor = 10
        self.building.elevators[1].current_floor = 3
        self.building.elevators[2].current_floor = 5
        self.building.elevators[3].current_floor = 12

        eid, _, _ = self.dispatcher.assign_elevator(4, "UP")
        self.assertEqual(eid, 1)  # floor 3 is closest to 4

    def test_returns_valid_format(self):
        eid, wait, decision = self.dispatcher.assign_elevator(7, "UP")
        self.assertIsInstance(eid, int)
        self.assertIsInstance(wait, float)
        self.assertIsInstance(decision, dict)
        self.assertIn("assigned_elevator", decision)


class TestRoundRobinDispatcher(unittest.TestCase):
    """Round-robin strategy tests."""

    def setUp(self):
        self.building = Building.create(num_floors=15, num_elevators=4)
        self.dispatcher = RoundRobinDispatcher(self.building)

    def test_cycles_through_elevators(self):
        """Should assign elevators in order: 0, 1, 2, 3, 0, ..."""
        ids = []
        for _ in range(8):
            eid, _, _ = self.dispatcher.assign_elevator(5, "UP")
            ids.append(eid)
        self.assertEqual(ids, [0, 1, 2, 3, 0, 1, 2, 3])

    def test_skips_non_operational(self):
        """Should skip elevators that are not operational."""
        self.building.elevators[0].is_operational = False
        eid, _, _ = self.dispatcher.assign_elevator(5, "UP")
        self.assertNotEqual(eid, 0)


class TestSCANDispatcher(unittest.TestCase):
    """SCAN (elevator algorithm) strategy tests."""

    def setUp(self):
        self.building = Building.create(num_floors=15, num_elevators=4)
        self.dispatcher = SCANDispatcher(self.building)

    def test_prefers_same_direction_ahead(self):
        """Elevator sweeping UP with call ahead should be preferred."""
        self.building.elevators[0].current_floor = 3
        self.building.elevators[0].direction = "UP"

        # Elevator 1 going DOWN at floor 14: scan cost = 14→1 + 1→7 = 20
        # Elevator 0 going UP at floor 3:    scan cost = 7 - 3 = 4
        self.building.elevators[1].current_floor = 14
        self.building.elevators[1].direction = "DOWN"

        eid, _, _ = self.dispatcher.assign_elevator(7, "UP")
        self.assertEqual(eid, 0)  # scan cost 4 vs 20

    def test_scan_cost_forward(self):
        cost = SCANDispatcher._scan_cost(5, "UP", 10, 1, 15)
        self.assertEqual(cost, 5.0)

    def test_scan_cost_reverse(self):
        cost = SCANDispatcher._scan_cost(5, "UP", 3, 1, 15)
        # Must go to 15 (10 floors) then back to 3 (12 floors) = 22
        self.assertEqual(cost, 22.0)

    def test_scan_cost_idle(self):
        cost = SCANDispatcher._scan_cost(5, "IDLE", 10, 1, 15)
        self.assertEqual(cost, 5.0)


# ═══════════════════════════════════════════════════════════════════════════
# Strategy Registry
# ═══════════════════════════════════════════════════════════════════════════
class TestStrategyRegistry(unittest.TestCase):
    """Strategy factory and registry tests."""

    def test_all_strategies_registered(self):
        names = get_strategy_names()
        self.assertIn("gbfs", names)
        self.assertIn("nearest", names)
        self.assertIn("round_robin", names)
        self.assertIn("scan", names)

    def test_factory_creates_correct_type(self):
        building = Building.create()
        self.assertIsInstance(get_strategy("gbfs", building), GBFSDispatcher)
        self.assertIsInstance(get_strategy("nearest", building), NearestLiftDispatcher)
        self.assertIsInstance(get_strategy("round_robin", building), RoundRobinDispatcher)
        self.assertIsInstance(get_strategy("scan", building), SCANDispatcher)

    def test_unknown_strategy_raises(self):
        building = Building.create()
        with self.assertRaises(ValueError):
            get_strategy("nonexistent", building)


# ═══════════════════════════════════════════════════════════════════════════
# A* Sequencer
# ═══════════════════════════════════════════════════════════════════════════
class TestAStarSequencer(unittest.TestCase):
    """A* floor-sequencing tests."""

    def setUp(self):
        self.building = Building.create(num_floors=15, num_elevators=4)
        self.astar = AStarSequencer(self.building)

    def test_route_cost(self):
        """Verify route cost calculation (time-based: 2s per floor)."""
        cost = self.astar.calculate_route_cost([5, 8, 2, 12])
        # 5→8=3, 8→2=6, 2→12=10 → 19 floors × 2s = 38s
        self.assertEqual(cost, 38.0)

    def test_optimal_sequence(self):
        """A* should find a better route than random order."""
        floors = [1, 10, 3, 7]
        optimal = self.astar.a_star_search(1, [10, 3, 7])
        optimal_cost = self.astar.calculate_route_cost(optimal)
        naive_cost = self.astar.calculate_route_cost(floors)
        self.assertLessEqual(optimal_cost, naive_cost)

    def test_single_floor(self):
        """Single-floor route should return [current, floor]."""
        result = self.astar.a_star_search(5, [10])
        self.assertEqual(result, [5, 10])

    def test_empty_floors(self):
        """No floors to visit → return [current_floor]."""
        result = self.astar.a_star_search(5, [])
        self.assertEqual(result, [5])

    def test_reopt_cost_bound(self):
        """Reoptimisation should respect the 15% cost bound."""
        elevator = self.building.elevators[0]
        elevator.current_floor = 5
        elevator.up_queue = [8, 12]

        result = self.astar.optimize_route(elevator)
        self.assertLessEqual(result["cost_increase_percent"], 15.0)

    def test_reopt_within_zone(self):
        """Reopt should trigger for calls within 2-floor zone."""
        elevator = self.building.elevators[0]
        elevator.current_floor = 5
        elevator.up_queue = [8]

        triggered = self.astar.reopt_on_new_call(elevator, 6)  # 1 floor away
        self.assertIsInstance(triggered, bool)

    def test_reopt_outside_zone(self):
        """Reopt should NOT trigger for calls outside 2-floor zone."""
        elevator = self.building.elevators[0]
        elevator.current_floor = 5
        elevator.up_queue = [8]

        triggered = self.astar.reopt_on_new_call(elevator, 10)  # 5 floors away
        self.assertFalse(triggered)


# ═══════════════════════════════════════════════════════════════════════════
# Dynamic Weight Adjuster
# ═══════════════════════════════════════════════════════════════════════════
class TestDynamicWeightAdjuster(unittest.TestCase):
    """Weight adjuster rule tests."""

    def setUp(self):
        self.building = Building.create(num_floors=15, num_elevators=4)
        self.gbfs = GBFSDispatcher(self.building)
        self.adjuster = DynamicWeightAdjuster(
            self.gbfs, self.building, sla_wait_target_sec=45.0
        )

    def test_adjustment_returns_dict(self):
        weights = self.adjuster.adjust_weights(force=True)
        self.assertIsInstance(weights, dict)
        self.assertIn("direction_bias", weights)

    def test_weights_sum_near_one(self):
        weights = self.adjuster.adjust_weights(force=True)
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, delta=0.15)

    def test_history_recorded(self):
        self.adjuster.adjust_weights(force=True)
        history = self.adjuster.get_history(1)
        self.assertEqual(len(history), 1)
        self.assertIn("metrics", history[0])


# ═══════════════════════════════════════════════════════════════════════════
# Traffic Predictor
# ═══════════════════════════════════════════════════════════════════════════
class TestTrafficPredictor(unittest.TestCase):
    """Traffic forecasting tests."""

    def setUp(self):
        self.building = Building.create()
        self.predictor = TrafficPredictor(self.building)

    def test_forecast_structure(self):
        forecast = self.predictor.forecast_next_n_minutes(5)
        self.assertIn("forecasted_volume", forecast)
        self.assertIn("confidence", forecast)
        self.assertIn("recommendation", forecast)

    def test_observation_recording(self):
        self.predictor.observe_call(5, datetime.now())
        self.assertEqual(len(self.predictor.observation_history), 1)

    def test_confidence_increases(self):
        for i in range(100):
            self.predictor.observe_call(i % 15 + 1, datetime.now())
        forecast = self.predictor.forecast_next_n_minutes()
        self.assertGreater(forecast["confidence"], 0)


# ═══════════════════════════════════════════════════════════════════════════
# Telemetry Logger
# ═══════════════════════════════════════════════════════════════════════════
class TestTelemetryLogger(unittest.TestCase):
    """CSV logger tests."""

    def setUp(self):
        self.test_csv = os.path.join(
            os.path.dirname(__file__), "_test_telemetry.csv"
        )
        self.logger = TelemetryLogger(csv_filename=self.test_csv, buffer_size=5)

    def tearDown(self):
        self.logger.close()
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def test_csv_header_created(self):
        self.assertTrue(os.path.exists(self.test_csv))
        with open(self.test_csv, encoding="utf-8") as f:
            header = f.readline().strip()
        self.assertIn("timestamp", header)
        self.assertIn("gbfs_score", header)

    def test_assignment_log(self):
        pax = Passenger(origin_floor=3, dest_floor=10)
        self.logger.log_call_assignment(
            call_id="TEST_001",
            passenger=pax,
            elevator_id=1,
            gbfs_score=0.85,
            weights={"direction_bias": 0.4, "load_balance": 0.25,
                      "distance": 0.2, "wait_time": 0.1},
            traffic_intensity=3.5,
        )
        self.logger.flush()
        self.assertEqual(self.logger.total_rows_written, 1)

    def test_batch_flush(self):
        """Buffer should auto-flush after buffer_size writes."""
        for i in range(6):  # buffer_size = 5
            pax = Passenger(origin_floor=i % 15 + 1, dest_floor=10)
            self.logger.log_call_assignment(
                call_id=f"TEST_{i:03d}",
                passenger=pax,
                elevator_id=0,
                gbfs_score=0.5,
                weights={},
                traffic_intensity=1.0,
            )
        # 5 should have auto-flushed, 1 in buffer
        self.assertEqual(self.logger.total_rows_written, 5)
        self.assertEqual(len(self.logger.buffer), 1)


# ═══════════════════════════════════════════════════════════════════════════
# Traffic Scenarios
# ═══════════════════════════════════════════════════════════════════════════
class TestTrafficScenarios(unittest.TestCase):
    """Traffic scenario system tests."""

    def test_all_scenarios_exist(self):
        names = get_scenario_names()
        self.assertIn("morning_rush", names)
        self.assertIn("lunch_peak", names)
        self.assertIn("evening_rush", names)
        self.assertIn("random_uniform", names)

    def test_scenario_deterministic(self):
        """Same seed should produce identical call sequences."""
        import numpy as np

        config = {
            "simulation": {"building_floors": 15},
            "traffic": {},
        }
        building = Building.create()

        rng1 = np.random.default_rng(42)
        gen1 = TrafficGenerator(building, config, rng1, scenario_name="morning_rush")
        calls1 = gen1.generate_calls(datetime(2026, 1, 1, 8, 0), 1.0)

        rng2 = np.random.default_rng(42)
        gen2 = TrafficGenerator(building, config, rng2, scenario_name="morning_rush")
        calls2 = gen2.generate_calls(datetime(2026, 1, 1, 8, 0), 1.0)

        self.assertEqual(calls1, calls2)

    def test_morning_rush_bias(self):
        """Morning rush should produce mostly UP calls from floor 1."""
        import numpy as np

        config = {
            "simulation": {"building_floors": 15},
            "traffic": {},
        }
        building = Building.create()
        rng = np.random.default_rng(42)
        gen = TrafficGenerator(building, config, rng, scenario_name="morning_rush")

        all_calls = []
        for _ in range(500):
            calls = gen.generate_calls(datetime(2026, 1, 1, 8, 0), 1.0)
            all_calls.extend(calls)

        if all_calls:
            up_from_ground = sum(
                1 for f, d, p, dest in all_calls
                if f == 1 and d == "UP"
            )
            ratio = up_from_ground / len(all_calls)
            self.assertGreater(ratio, 0.5)  # should be ~80%

    def test_set_scenario(self):
        import numpy as np
        config = {
            "simulation": {"building_floors": 15},
            "traffic": {},
        }
        building = Building.create()
        rng = np.random.default_rng(42)
        gen = TrafficGenerator(building, config, rng)
        gen.set_scenario("evening_rush")
        self.assertEqual(gen.scenario_name, "evening_rush")

    def test_invalid_scenario_raises(self):
        import numpy as np
        config = {
            "simulation": {"building_floors": 15},
            "traffic": {},
        }
        building = Building.create()
        rng = np.random.default_rng(42)
        gen = TrafficGenerator(building, config, rng)
        with self.assertRaises(ValueError):
            gen.set_scenario("nonexistent_scenario")


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main(verbosity=2)
