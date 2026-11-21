"""P2 基础几何工具测试（不检验未定的定位精度模型）。"""

import csv
from dataclasses import fields
import math
import unittest

from geometry_B.p2_two_station_tools import (
    TwoStationResultRow, distance_2d, intersection_angle_deg,
    straight_line_travel_time, target_ranges,
)


class TwoStationToolsTests(unittest.TestCase):
    def test_distance_and_units(self):
        self.assertEqual(distance_2d((0, 0), (3, 4)), 5)
        self.assertEqual(distance_2d((3, 4), (3, 4)), 0)
        self.assertEqual(target_ranges((0, 0), (3, 4), (0, -2)), (5, 2))
        self.assertEqual(straight_line_travel_time((0, 0), (3, 4), 2), 2.5)
        for speed in (0, -1, float("nan"), float("inf")):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                straight_line_travel_time((0, 0), (3, 4), speed)
        with self.assertRaises(ValueError):
            distance_2d((0, float("nan")), (1, 1))

    def test_angle_boundaries_and_coincident(self):
        target = (0, 0)
        self.assertAlmostEqual(intersection_angle_deg(target, (1, 0), (0, 1)), 90)
        self.assertAlmostEqual(intersection_angle_deg(target, (1, 0), (2, 0)), 0)
        self.assertAlmostEqual(intersection_angle_deg(target, (1, 0), (-2, 0)), 180)
        self.assertAlmostEqual(intersection_angle_deg(target, (1, 0), (1, 1e-9)),
                               math.degrees(math.atan2(1e-9, 1)))
        with self.assertRaises(ValueError):
            intersection_angle_deg(target, target, (0, 1))
        with self.assertRaises(ValueError):
            intersection_angle_deg(target, (1, 0), target)

    def test_result_schema_does_not_fabricate_precision(self):
        row = TwoStationResultRow("V1", "V3", 5.0, 10.0, 20.0, 30.0)
        result = row.as_csv_row()
        self.assertEqual(result["vehicle_a_id"], "V1")
        self.assertIsNone(result["accuracy_metric_value"])
        self.assertIsNone(result["vehicle_a_travel_time_s"])
        self.assertEqual(list(result), [f.name for f in fields(TwoStationResultRow)])
        self.assertIn("accuracy_metric_unit", result)


if __name__ == "__main__":
    unittest.main()
