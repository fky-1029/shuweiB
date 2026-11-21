"""P2 最终退化、仰角约束与剪枝覆盖验证。"""
import math
import unittest

from geometry_B.p2_final_analysis import (
    audit_pending, cap_experiment, degeneration_series, elevation_deg,
    filter_elevation, read_nominal_pairs,
)
from geometry_B.p2_two_station_optimize import read_candidates
from shared.constants import CAMERA_HEIGHT, TARGETS


class FinalAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read_candidates()
        cls.nominal = read_nominal_pairs()

    def test_degeneracy_symmetric_and_finite_near_right_angle(self):
        rows = degeneration_series(20, 20, (0, 1, 90, 179, 180))
        self.assertEqual(len(rows), 5)
        self.assertTrue(math.isinf(rows[0]["rmse_m"]))
        self.assertTrue(math.isinf(rows[-1]["rmse_m"]))
        self.assertAlmostEqual(rows[1]["rmse_m"], rows[3]["rmse_m"])
        self.assertGreater(rows[1]["rmse_m"], rows[2]["rmse_m"])
        self.assertAlmostEqual(rows[2]["rmse_m"], math.radians(1)*20*math.sqrt(2))

    def test_pitch_recalculates_station_feasibility(self):
        target = (TARGETS[1]["x"], TARGETS[1]["y"])
        dz = TARGETS[1]["z"] - CAMERA_HEIGHT
        self.assertAlmostEqual(elevation_deg((target[0] + dz / math.tan(math.radians(79)),
                                               target[1])), 79)
        original = self.data[1]["confirmed"]
        self.assertIn((8., 67.5), original)
        self.assertNotIn((8., 67.5), filter_elevation(self.data, 79.5)[1]["confirmed"])
        self.assertIn((8., 67.5), original)  # no input mutation
        small = filter_elevation({1: {"confirmed": {(8., 67.5): 18., (7., 67.5): 18.},
                                      "pending": {(6., 75.5): None}}}, 79)
        self.assertEqual(set(small[1]["confirmed"]), {(7., 67.5)})
        self.assertNotIn((6., 75.5), small[1]["pending"])

    def test_nominal_ties_exact_and_constraint_certification(self):
        rows = sorted(self.nominal, key=lambda row: row["rmse_m"])
        self.assertEqual((rows[0]["vehicle_a"], rows[0]["vehicle_b"]), (1, 3))
        tied = next(r for r in rows if (r["vehicle_a"], r["vehicle_b"]) == (1, 5))
        self.assertEqual(rows[0]["rmse_m"], tied["rmse_m"])
        report = cap_experiment(self.data, self.nominal, 80.)
        self.assertEqual({(r["vehicle_a"], r["vehicle_b"]) for r in report["ties"]},
                         {(1, 3), (1, 5)})
        self.assertTrue(report["winner"]["travel_time_a_s"] < 30)
        self.assertTrue(report["winner"]["travel_time_b_s"] < 30)

    def test_radius_bound_audit_matches_small_unpruned_bruteforce(self):
        # Real T2 target, small samples with status mix; compare scalar full pairs.
        t = (TARGETS[1]["x"], TARGETS[1]["y"])
        sample = {1: {"confirmed": {(8., 67.5): 1.},
                      "pending": {(8., 77.5): None, (90., 90.): None}},
                  2: {"confirmed": {(6., 75.5): 1.},
                      "pending": {(6., 69.5): None, (99., 99.): None}}}
        from geometry_B.p2_localization_accuracy import calculate_localization_metrics
        limit = 0.25
        full = [(p, q, calculate_localization_metrics(p, q, t)["rmse_m"])
                for p in sample[1]["confirmed"] | sample[1]["pending"]
                for q in sample[2]["confirmed"] | sample[2]["pending"]
                if p in sample[1]["pending"] or q in sample[2]["pending"]]
        actual = audit_pending(sample, limit)
        self.assertEqual(actual["total_screened_pair_combinations"], 9)
        self.assertEqual(len(actual["pending_strict_improvers"]),
                         sum(rmse < limit for _, _, rmse in full))

    def test_tighter_cap_requires_new_search_and_has_no_pending_improvers(self):
        for cap in (79.5, 79.):
            with self.subTest(cap=cap):
                result = cap_experiment(self.data, self.nominal, cap)
                self.assertEqual(result["pair_count"], 10)
                self.assertGreater(result["winner"]["rmse_m"], .14441638392829942)
                self.assertEqual({(r["vehicle_a"], r["vehicle_b"]) for r in result["ties"]},
                                 {(1, 3), (1, 5)})
                audit = audit_pending(filter_elevation(self.data, cap),
                                      result["winner"]["rmse_m"])
                self.assertEqual(audit["pending_strict_improvers"], [])


if __name__ == "__main__":
    unittest.main()
