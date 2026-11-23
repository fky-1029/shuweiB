"""双站水平定位一阶误差传播的独立数值检验。"""
import math
import unittest

import numpy as np

from geometry_B.p2_localization_accuracy import (
    DEGENERATE_SIN_THRESHOLD, calculate_localization_metrics,
)
from shared.constants import TARGETS


class LocalizationAccuracyTests(unittest.TestCase):
    def test_orthogonal(self):
        result = calculate_localization_metrics((-20, 0), (0, -20), (0, 0))
        self.assertEqual(result["r1_m"], 20)
        self.assertEqual(result["r2_m"], 20)
        self.assertAlmostEqual(result["baseline_m"], 20 * math.sqrt(2))
        self.assertEqual(result["alpha1_deg"], 0)
        self.assertEqual(result["alpha2_deg"], 90)
        self.assertAlmostEqual(result["gamma_deg"], 90)
        self.assertAlmostEqual(result["rmse_m"], math.radians(1) * 20 * math.sqrt(2))
        self.assertAlmostEqual(result["rmse_m"], 0.4937, places=4)
        self.assertFalse(result["degenerate"])

    def test_collinear_same_and_opposite(self):
        for second, gamma in (((-10, 0), 0), ((10, 0), 180), ((-20, 0), 0)):
            with self.subTest(second=second):
                result = calculate_localization_metrics((-20, 0), second, (0, 0))
                self.assertAlmostEqual(result["gamma_deg"], gamma)
                self.assertTrue(result["degenerate"])
                self.assertTrue(math.isinf(result["rmse_m"]))

    def test_swap_stations_and_sigma_scale(self):
        a, b, t = (2., -3.), (-9., 8.), (4., 5.)
        first = calculate_localization_metrics(a, b, t)
        swapped = calculate_localization_metrics(b, a, t)
        doubled = calculate_localization_metrics(a, b, t, sigma_deg=2)
        for field in ("baseline_m", "gamma_deg", "rmse_m"):
            self.assertAlmostEqual(first[field], swapped[field])
        self.assertAlmostEqual(doubled["rmse_m"], 2 * first["rmse_m"])
        self.assertEqual((first["alpha1_deg"], first["alpha2_deg"]),
                         (swapped["alpha2_deg"], swapped["alpha1_deg"]))

    def test_jacobian_inverse_covariance_independent_check(self):
        # alpha_i=atan2(y-yi,x-xi)，J_i=(-dy_i/r_i², dx_i/r_i²)。
        # 独立地从测角方程的雅可比矩阵求协方差，而非复写解析公式。
        for a, b, t in (
            ((-20., 0.), (0., -20.), (0., 0.)),
            ((2., -3.), (-9., 8.), (4., 5.)),
            ((0., 0.), (1., 0.01), (12., 15.)),
        ):
            with self.subTest(station1=a, station2=b):
                metrics = calculate_localization_metrics(a, b, t, sigma_deg=1.7)
                j = np.array([[-(t[1]-p[1]) / math.dist(t, p)**2,
                                (t[0]-p[0]) / math.dist(t, p)**2] for p in (a, b)])
                sigma = math.radians(1.7)
                covariance = np.linalg.inv(j) @ np.diag([sigma**2, sigma**2]) @ np.linalg.inv(j).T
                self.assertAlmostEqual(metrics["rmse_m"], math.sqrt(np.trace(covariance)), places=10)

    def test_threshold_only_rejects_extremely_small_angles(self):
        almost_collinear = calculate_localization_metrics((-20, 0), (-10, 1e-11), (0, 0))
        self.assertTrue(almost_collinear["degenerate"])
        self.assertTrue(math.isinf(almost_collinear["rmse_m"]))
        small_but_not_numerically_degenerate = calculate_localization_metrics(
            (-20, 0), (-10, 1e-8), (0, 0))
        self.assertFalse(small_but_not_numerically_degenerate["degenerate"])
        self.assertTrue(math.isfinite(small_but_not_numerically_degenerate["rmse_m"]))
        self.assertEqual(DEGENERATE_SIN_THRESHOLD, 1e-12)

    def test_undefined_azimuth_and_invalid_inputs(self):
        for a, b, t, sigma in (
            ((0, 0), (0, 1), (0, 0), 1),
            ((1, 0), (0, 0), (0, 0), 1),
            ((float("nan"), 0), (0, 1), (0, 0), 1),
            ((1,), (0, 1), (0, 0), 1),
            ((1, 0), (0, 1), (0, 0), 0),
            ((1, 0), (0, 1), (0, 0), math.inf),
        ):
            with self.subTest(a=a, b=b, sigma=sigma), self.assertRaises(ValueError):
                calculate_localization_metrics(a, b, t, sigma)

    def test_t2_uses_shared_coordinate_convention(self):
        t2 = TARGETS[1]
        self.assertAlmostEqual(t2["x"], 50 + 45 * math.cos(math.radians(150)))
        self.assertAlmostEqual(t2["y"], 50 + 45 * math.sin(math.radians(150)))
        result = calculate_localization_metrics((20., 60.), (30., 90.), (t2["x"], t2["y"]))
        self.assertTrue(0 <= result["alpha1_deg"] < 360)
        self.assertTrue(0 <= result["alpha2_deg"] < 360)
        self.assertTrue(0 <= result["gamma_deg"] <= 180)
        self.assertFalse(result["degenerate"])


if __name__ == "__main__":
    unittest.main()
