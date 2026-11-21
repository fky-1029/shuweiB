"""P2(1) 双站精确离散搜索及待验证点分析测试。"""
import math
import unittest

import numpy as np

from geometry_B.p2_localization_accuracy import calculate_localization_metrics
from geometry_B.p2_two_station_optimize import search_pair, optimize, read_candidates
from shared.constants import TARGETS


class OptimizeTests(unittest.TestCase):
    def test_exhaustive_matches_scalar_bruteforce(self):
        target = (1., 2.)
        a = {(-3., 0.): 1., (2., -4.): 1., (4., 7.): 1.}
        b = {(2., 7.): 1., (-3., 3.): 1., (4., 7.): 1., (1., 2.): 1.}
        expected = min((calculate_localization_metrics(p, q, target)["rmse_m"], p, q)
                       for p in a for q in b if q != target)
        actual = search_pair(a, b, target, block_size=2)
        self.assertAlmostEqual(actual["rmse_m"], expected[0])
        self.assertEqual(actual["stations"], expected[1:])

    def test_near_degenerate_and_radius_bound(self):
        t = (0., 0.)
        a = {(1., 0.): 1., (100., 0.): 1.}
        b = {(0., 1.): 1., (2., 0.): 1., (0., 100.): 1.}
        answer = search_pair(a, b, t, block_size=1)
        self.assertEqual(answer["stations"], ((1., 0.), (0., 1.)))
        self.assertAlmostEqual(answer["rmse_m"], math.radians(1) * math.sqrt(2))

    def test_pending_only_improvement_and_all_ten_pairs(self):
        target = (0., 0.)
        data = {k: {"confirmed": {(k + 2., 0.): 1., (0., k + 2.): 1.},
                    "pending": {(-1., 0.): None}} for k in range(1, 6)}
        pairs, winner, potential = optimize(data, target)
        self.assertEqual(len(pairs), 10)
        self.assertEqual(len(potential), 10)
        self.assertEqual({(r["vehicle_a"], r["vehicle_b"]) for r in pairs},
                         {(i, j) for i in range(1, 6) for j in range(i+1, 6)})
        self.assertTrue(any(p["geometric_better_pairs"] for p in potential))
        self.assertTrue(math.isfinite(winner["rmse_m"]))
        check = search_pair({(1., 0.): False, (0., 1.): True},
                            {(0., 1.): False, (-1., 0.): True}, target,
                            incumbent=1., require_pending=True, block_size=1)
        self.assertEqual(check["improving_pairs"], 1)
        self.assertEqual(check["promising_pending_a"], {(0., 1.)})
        self.assertEqual(check["promising_pending_b"], {(-1., 0.)})

    def test_real_csv_status_and_full_screen(self):
        data = read_candidates()
        self.assertEqual(len(data), 5)
        self.assertEqual([len(data[k]["confirmed"]) for k in range(1, 6)],
                         [10111, 8141, 12767, 8045, 18522])
        self.assertEqual([len(data[k]["pending"]) for k in range(1, 6)],
                         [12579, 13180, 12162, 16208, 6324])
        self.assertEqual((TARGETS[1]["x"], TARGETS[1]["y"]),
                         (50 + 45 * math.cos(math.radians(150)), 72.5))


if __name__ == "__main__":
    unittest.main()
