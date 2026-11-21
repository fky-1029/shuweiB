"""预计算可观测坐标读取接口与综合几何判定一致性测试。"""

import csv
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from geometry_B.geometry_debug import make_observability_evaluator, sample_observability_grid
from shared.constants import (
    FIELD_SIZE, TARGETS, _load_observable_points, get_observable_points,
)


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "shared" / "observable_points"


class ObservablePointsTests(unittest.TestCase):
    def test_all_targets_match_full_geometry_grid(self):
        """逐目标核对整张网格，不仅抽查已保存的合法点。"""
        for target in TARGETS:
            target_id = f"T{target['id']}"
            with self.subTest(target=target_id):
                points = get_observable_points(target_id)
                with (DATA_DIRECTORY / f"{target_id}_0p5m.csv").open(
                    encoding="utf-8", newline=""
                ) as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(reader.fieldnames, ["x_east_m", "y_north_m"])
                    csv_points = tuple(
                        (float(row["x_east_m"]), float(row["y_north_m"]))
                        for row in reader
                    )
                self.assertEqual(points, csv_points)
                self.assertEqual(len(points), len(set(points)))
                self.assertTrue(all(
                    0 <= x <= FIELD_SIZE and 0 <= y <= FIELD_SIZE
                    and (x * 2).is_integer() and (y * 2).is_integer()
                    for x, y in points
                ))
                x_values, y_values, mask = sample_observability_grid(
                    make_observability_evaluator(target), spacing=0.5
                )
                self.assertEqual(mask.shape, (201, 201))
                expected = tuple(
                    (float(x_values[i]), float(y_values[j]))
                    for j, i in zip(*mask.nonzero())
                )
                self.assertEqual(points, expected)
                self.assertEqual(len(points), int(mask.sum()))
                self.assertEqual(mask.size, 40401)

    def test_targets_distinct_and_t1_matches_existing_csv(self):
        sets = [set(get_observable_points(f"T{i}")) for i in (1, 2, 3)]
        self.assertEqual(len(sets), 3)
        self.assertNotEqual(sets[0], sets[1])
        self.assertNotEqual(sets[0], sets[2])
        self.assertNotEqual(sets[1], sets[2])
        existing = Path(__file__).resolve().parents[1] / "figures" / "p1_t1_observable_points_0p5m.csv"
        with existing.open(encoding="utf-8", newline="") as stream:
            rows = csv.DictReader(stream)
            self.assertEqual(
                get_observable_points("T1"),
                tuple((float(row["x_east_m"]), float(row["y_north_m"])) for row in rows),
            )

    def test_read_outside_repository_and_cache(self):
        _load_observable_points.cache_clear()
        original_open = Path.open
        with TemporaryDirectory() as temporary, patch(
            "pathlib.Path.open", autospec=True, side_effect=original_open
        ) as opened:
            old_directory = Path.cwd()
            try:
                os.chdir(temporary)
                first = get_observable_points("T2")
                second = get_observable_points("T2")
            finally:
                os.chdir(old_directory)
            self.assertIs(first, second)
            self.assertEqual(opened.call_count, 1)

    def test_invalid_target(self):
        for value in ("T4", "t1", "../../T1", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    get_observable_points(value)


if __name__ == "__main__":
    unittest.main()
