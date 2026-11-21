"""P2(1) 车辆直线行驶合法性、时间下界与三态分类测试。"""
import math
import unittest

from geometry_B.p2_vehicle_reachability import (
    CONFIRMED_REACHABLE, CONFIRMED_UNREACHABLE, PATH_UNVERIFIED,
    ReachabilityIndex, assess_station, straight_path_is_legal,
)
from shared.constants import BUILDINGS, FIELD_SIZE, VEHICLE_RADIUS, get_observable_points


class ReachabilityTests(unittest.TestCase):
    def test_distance_90_meter_boundary(self):
        result = assess_station(1, (5, 5), (95, 5), buildings=[])
        self.assertEqual(result.euclidean_distance_m, 90)
        self.assertEqual(result.status, CONFIRMED_REACHABLE)
        self.assertEqual(result.travel_time_s, 30)
        beyond = assess_station(1, (5, 5), (95.0001, 5), buildings=[])
        self.assertEqual(beyond.status, CONFIRMED_UNREACHABLE)
        self.assertFalse(beyond.passes_distance_screen)
        self.assertIsNone(beyond.travel_time_s)

    def test_clear_direct_route_and_coincident_start(self):
        result = assess_station(1, (5, 5), (10, 10))
        self.assertEqual(result.status, CONFIRMED_REACHABLE)
        self.assertAlmostEqual(result.path_length_m, math.sqrt(50))
        self.assertAlmostEqual(result.travel_time_s, math.sqrt(50) / 3)
        self.assertEqual(assess_station(1, (5, 5), (5, 5)).travel_time_s, 0)

    def test_blocked_middle_and_corner_grazing(self):
        # Both endpoints legal, but the B1 rectangle lies across the path.
        self.assertTrue(straight_path_is_legal((10, 21), (20.5, 21)))
        self.assertFalse(straight_path_is_legal((10, 21), (40, 21)))
        result = assess_station(1, (10, 21), (40, 21))
        self.assertEqual(result.status, PATH_UNVERIFIED)
        self.assertTrue(result.passes_distance_screen)
        self.assertIsNone(result.path_length_m)
        self.assertIsNone(result.travel_time_s)
        # The segment passes 1 m away from the corner (22,16); a zero-radius
        # center can pass but a radius-1.5 disk clips it between the endpoints.
        start, end = (17, 15), (27, 15)
        self.assertTrue(straight_path_is_legal(start, end, vehicle_radius=0))
        self.assertFalse(straight_path_is_legal(start, end))

    def test_boundary_and_tangent(self):
        self.assertTrue(straight_path_is_legal((VEHICLE_RADIUS, 50),
                                              (VEHICLE_RADIUS, 60), buildings=[]))
        self.assertFalse(straight_path_is_legal((VEHICLE_RADIUS - .01, 50),
                                               (10, 50), buildings=[]))
        self.assertFalse(straight_path_is_legal((FIELD_SIZE - VEHICLE_RADIUS + .01, 50),
                                               (90, 50), buildings=[]))
        # Tangency to B1 west face is allowed; a strictly closer segment is not.
        self.assertTrue(straight_path_is_legal((22 - VEHICLE_RADIUS, 12),
                                              (22 - VEHICLE_RADIUS, 28)))
        self.assertFalse(straight_path_is_legal((22 - VEHICLE_RADIUS + .01, 12),
                                               (22 - VEHICLE_RADIUS + .01, 28)))
        # Distance to B1's corner is 1.5 m at an interior point of the segment.
        self.assertTrue(straight_path_is_legal((17, 14.5), (27, 14.5)))
        self.assertFalse(straight_path_is_legal((17, 14.51), (27, 14.51)))

    def test_query_and_count_invariants(self):
        index = ReachabilityIndex(((5, 5), (40, 21), (98.5, 98.5)),
                                  vehicles=[{"id": 1, "x": 10, "y": 21}])
        self.assertEqual(index.get(1, (5, 5)).status, CONFIRMED_REACHABLE)
        self.assertEqual(index.get(1, (40, 21)).status, PATH_UNVERIFIED)
        row = index.summary()[0]
        self.assertEqual(row["total_observable"], 3)
        self.assertEqual(row["distance_screen_candidates"] +
                         row["distance_screen_excluded"], 3)
        self.assertEqual(row["confirmed_reachable"] + row["path_unverified"],
                         row["distance_screen_candidates"])
        with self.assertRaises(KeyError):
            index.get(1, (6, 6))
        with self.assertRaises(ValueError):
            ReachabilityIndex(((5, 5), (5, 5)))

    def test_t2_data_integrity(self):
        points = get_observable_points("T2")
        self.assertEqual(len(points), 26037)
        self.assertEqual(len(points), len(set(points)))
        self.assertTrue(all(math.isfinite(x) and math.isfinite(y) and
                            VEHICLE_RADIUS <= x <= FIELD_SIZE - VEHICLE_RADIUS and
                            VEHICLE_RADIUS <= y <= FIELD_SIZE - VEHICLE_RADIUS
                            for x, y in points))
        self.assertEqual(len(BUILDINGS), 5)


if __name__ == "__main__":
    unittest.main()
