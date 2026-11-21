"""P1 理论圆周采样与时间下界、浮点边界和净空检查。"""
import math
import unittest

import numpy as np
from scipy.optimize import minimize_scalar

from geometry_B.p1_circle_analysis import (
    BUILDINGS, CAMERA_HEIGHT, KNOWN_WITNESS, R_STAR, TARGET,
    circle_point, choose_actual_sample, compare, gimbal_aim_time_s, parking_clearance_m,
    sight_clearance_m, vehicle_positions,
)
from shared.geometry_interface import check_observation_feasibility


class P1CircleTests(unittest.TestCase):
    def test_witness_attains_angle_bound_with_actual_interface(self):
        result = check_observation_feasibility(KNOWN_WITNESS, TARGET)
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["horizontal_distance"], R_STAR, places=12)
        self.assertEqual(result["elevation_angle"], 80.)

    def test_rounding_keeps_raw_judgment_and_strict_final_judgment(self):
        point = circle_point(7)
        self.assertFalse(point["raw_feasible"])
        self.assertFalse(point["raw_gimbal_valid"])
        self.assertEqual(point["rounding_adjustment_steps"], 1)
        self.assertTrue(point["feasible"])
        self.assertTrue(point["gimbal_valid"])
        self.assertLessEqual(abs(point["radius_deviation_m"]), 1e-11)
        self.assertEqual(circle_point(260)["rounding_adjustment_steps"], 0)

    def test_clearance_diagnostic_vs_independent_numeric_minimization(self):
        for point in (KNOWN_WITNESS, (83.32440521981547, 62.53312836032199)):
            with self.subTest(point=point):
                a = np.array((*point, CAMERA_HEIGHT))
                b = np.array(TARGET)
                expected = math.inf
                for building in BUILDINGS:
                    low = np.array((building["x_min"], building["y_min"], 0))
                    high = np.array((building["x_max"], building["y_max"], building["height"]))
                    def distance(t):
                        p = a + t * (b-a)
                        return np.linalg.norm(np.maximum(low-p, 0) + np.minimum(high-p, 0))
                    result = minimize_scalar(distance, bounds=(0, 1), method="bounded",
                                             options={"xatol": 1e-14})
                    expected = min(expected, distance(0), distance(1), result.fun)
                self.assertAlmostEqual(sight_clearance_m(point), expected, places=7)
                self.assertGreaterEqual(parking_clearance_m(point), 0)

    def test_five_vehicles_and_lower_bounds(self):
        circle = [circle_point(angle) for angle in range(360)]
        self.assertEqual(sum(c["feasible"] for c in circle), 284)
        self.assertEqual(sum(c["raw_feasible"] for c in circle), 262)
        self.assertEqual(sum(c["rounding_adjustment_steps"] > 0 for c in circle), 31)
        rows = compare(circle)
        self.assertEqual(len(rows), 284 * 5)
        self.assertEqual(set(vehicle_positions()), {"V1", "V2", "V3", "V4", "V5"})
        self.assertTrue(all(row["time_type"] == "straight_line_lower_bound" for row in rows))
        self.assertTrue(all(row["deployment_time_s"] >= row["gimbal_aim_time_s"] for row in rows))
        self.assertAlmostEqual(gimbal_aim_time_s(KNOWN_WITNESS),
                               max(80, abs((math.degrees(math.atan2(TARGET[1]-KNOWN_WITNESS[1],
                                   TARGET[0]-KNOWN_WITNESS[0]))+180)%360-180))/30,
                               places=10)

    def test_actual_sample_tie_uses_separate_clearance_metrics(self):
        with self.assertRaises(ValueError):
            choose_actual_sample(compare([circle_point(260)]))
        rows = [
            {"time_type": "actual_path", "deployment_time_s": 5.,
             "sight_clearance_m": 2., "parking_clearance_m": 8.,
             "circle_angle_deg": 0, "vehicle_id": "V1"},
            {"time_type": "actual_path", "deployment_time_s": 5. + 0.5e-9,
             "sight_clearance_m": 3., "parking_clearance_m": 1.,
             "circle_angle_deg": 1, "vehicle_id": "V2"},
        ]
        self.assertEqual(choose_actual_sample(rows)["vehicle_id"], "V2")
        self.assertEqual(choose_actual_sample(rows, time_tolerance_s=0)["vehicle_id"], "V1")

    def test_path_injection_rejects_nonphysical_travel_time(self):
        with self.assertRaises(ValueError):
            compare([circle_point(260)], travel_time=lambda start, end: 0)


if __name__ == "__main__":
    unittest.main()
