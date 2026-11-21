"""P1 遮挡回归测试；仅依据题面和可独立核查的单建筑场景。"""

import sys
import unittest
from pathlib import Path

if __name__ == "__main__" and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.constants import BUILDINGS, CAMERA_HEIGHT
from shared.geometry_interface import check_building_occlusion


B1 = [BUILDINGS[0]]  # x=[22,34], y=[16,26], 高 20 m
CLEAR = (False, None)
BLOCKED = (True, 1)


class BuildingOcclusionTests(unittest.TestCase):
    def check_cases(self, cases):
        for name, vehicle, target, expected in cases:
            with self.subTest(case=name):
                try:
                    actual = check_building_occlusion(vehicle, target, B1)
                except NotImplementedError:
                    self.skipTest("待实现 check_building_occlusion")
                self.assertEqual(actual, expected)

    def test_segment_and_axis_parallel_cases(self):
        self.check_cases([
            ("平行 x 轴，穿过建筑内部", (10, 21), (40, 21, CAMERA_HEIGHT), BLOCKED),
            ("平行 y 轴，穿过建筑内部", (28, 10), (28, 30, CAMERA_HEIGHT), BLOCKED),
            ("平行 x 轴，在建筑侧面之外", (10, 15), (40, 15, CAMERA_HEIGHT), CLEAR),
            ("垂直视线，远离建筑", (10, 10), (10, 10, 50), CLEAR),
            ("只有越过目标的延长线才碰到建筑", (10, 21), (15, 21, CAMERA_HEIGHT), CLEAR),
        ])

    def test_contact_without_entering_interior(self):
        self.check_cases([
            ("沿南侧面", (10, 16), (40, 16, CAMERA_HEIGHT), BLOCKED),
            ("只擦过一条竖棱", (10, 28), (34, 4, CAMERA_HEIGHT), BLOCKED),
            ("只擦过屋顶顶点 (22,16,20)", (10, 28), (34, 4, 38), BLOCKED),
            ("目标端点碰到西侧面", (10, 21), (22, 21, CAMERA_HEIGHT), BLOCKED),
        ])

    def test_roof_contact_and_both_sides(self):
        # 在 x=22 处进入 B1 的平面范围，恰好是线段中点；随后视线继续升高。
        self.check_cases([
            ("略低于屋顶进入", (10, 21), (34, 21, 37.98), BLOCKED),
            ("恰好擦到屋顶西棱 (22,21,20)", (10, 21), (34, 21, 38), BLOCKED),
            ("从屋顶上方越过", (10, 21), (34, 21, 38.02), CLEAR),
        ])


if __name__ == "__main__":
    unittest.main()
