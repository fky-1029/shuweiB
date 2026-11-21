"""P1 网格候选报告及连续候选单点接口测试。"""
import math
import unittest

from geometry_B.p1_optimal_station import (
    GRID_CANDIDATE,
    evaluate_station,
    validate_continuous_candidate,
    verify_grid_candidate,
)


class P1StationAuditTests(unittest.TestCase):
    def test_verified_grid_candidate(self):
        result = verify_grid_candidate()
        self.assertTrue(result["feasible"])
        self.assertEqual(tuple(result["position_xy_m"]), GRID_CANDIDATE)
        self.assertAlmostEqual(result["r_horizontal_m"], 7.58544862993, places=11)
        self.assertAlmostEqual(result["theta_elevation_deg"], 79.9956212159, places=10)
        self.assertAlmostEqual(result["Q_inverse_m"], 0.131831358801, places=12)
        self.assertIn("不是连续全局最优", result["status"])

    def test_continuous_point_validation_does_not_claim_optimality(self):
        result = validate_continuous_candidate((80.0, 76.0))
        self.assertTrue(result["feasible"])
        self.assertIn("未证明", result["status"])

    def test_invalid_coordinates_rejected(self):
        for point in ((1.0,), (float("nan"), 2.0)):
            with self.subTest(point=point), self.assertRaises(ValueError):
                evaluate_station(point)

    def test_theoretical_lower_bound_value(self):
        lower_bound = 43.0 / math.tan(math.radians(80.0))
        self.assertAlmostEqual(lower_bound, 7.58206017046, places=10)
        self.assertLess(lower_bound, 7.58544862993)


if __name__ == "__main__":
    unittest.main()
