"""P1 车辆站位与综合观测约束回归测试。"""

import math
import unittest

from shared.constants import BUILDINGS, CAMERA_HEIGHT, FIELD_SIZE, VEHICLE_RADIUS
from shared.geometry_interface import (
    check_observation_feasibility,
    is_vehicle_position_valid,
)


# 输入：车辆中心、场地边长、车辆半径、建筑列表；输出：站位是否合法。
# 按题面「不得越过场地边界、不得进入建筑内部」设置期望，不固定数值容差。
# B1 西南角 (22, 16)；偏移 (0.9, 1.2) 的长度为 1.5 m。
EDGE_OFFSET = 0.01  # 测试点间距，不是判定容差
VEHICLE_POSITION_CASES = (
    ("恰好接触场地边界", (VEHICLE_RADIUS, 50.0), True),
    ("恰好接触场地东北角两条边", (FIELD_SIZE - VEHICLE_RADIUS, FIELD_SIZE - VEHICLE_RADIUS), True),
    ("圆盘越过场地边界", (VEHICLE_RADIUS - EDGE_OFFSET, 50.0), False),
    ("圆盘越过场地北边界", (50.0, FIELD_SIZE - VEHICLE_RADIUS + EDGE_OFFSET), False),
    ("圆盘中心在 B1 内部", (28.0, 21.0), False),
    ("圆盘中心在 B1 边上", (22.0, 21.0), False),
    ("恰好接触 B1 西侧边", (22.0 - VEHICLE_RADIUS, 21.0), True),
    ("圆盘从西侧进入 B1", (22.0 - VEHICLE_RADIUS + EDGE_OFFSET, 21.0), False),
    ("恰好接触 B1 西南角", (22.0 - 0.9, 16.0 - 1.2), True),
    ("圆盘从西南角进入 B1", (22.0 - 0.9 + EDGE_OFFSET, 16.0 - 1.2), False),
    ("圆盘在 B1 西南角外留有间距", (22.0 - 0.9 - EDGE_OFFSET, 16.0 - 1.2), True),
)


class VehiclePositionTests(unittest.TestCase):
    def test_vehicle_disk_constraints(self):
        for name, center, expected in VEHICLE_POSITION_CASES:
            with self.subTest(case=name):
                actual = is_vehicle_position_valid(
                    center, BUILDINGS, FIELD_SIZE, VEHICLE_RADIUS
                )
                self.assertIs(actual, expected)

    def test_default_constants_and_buildings(self):
        self.assertTrue(is_vehicle_position_valid((VEHICLE_RADIUS, 50.0)))
        self.assertFalse(is_vehicle_position_valid((28.0, 21.0)))

    def test_custom_parameters_and_empty_buildings(self):
        self.assertTrue(is_vehicle_position_valid((2.0, 2.0), [], 4.0, 2.0))
        self.assertFalse(is_vehicle_position_valid((1.99, 2.0), [], 4.0, 2.0))
        self.assertTrue(is_vehicle_position_valid((28.0, 21.0), []))

    def test_corner_distance_not_expanded_rectangle(self):
        # 此点落在错误的「矩形各边外扩 1.5m」范围内，实际离角点更远。
        self.assertTrue(is_vehicle_position_valid((20.9, 14.9), BUILDINGS))


class ObservationFeasibilityTests(unittest.TestCase):
    def test_three_constraints_contribute_to_feasibility(self):
        # 除特意违例的一项外，其余约束均满足。只约束最终结果，
        # 不规定提前返回、失败原因优先级或多建筑 ID 的选择方式。
        cases = (
            ("三项均满足", (10, 10), (15, 10, 7), True),
            ("仅车辆圆盘越界", (1, 10), (6, 10, 7), False),
            ("仅视线被 B1 遮挡", (10, 21), (40, 21, 10), False),
            ("仅仰角超限", (10, 10), (10, 10, 50), False),
        )
        for name, vehicle, target, expected in cases:
            with self.subTest(case=name):
                result = check_observation_feasibility(vehicle, target, BUILDINGS)
                self.assertEqual(set(result), {
                    "feasible", "horizontal_distance", "elevation_angle", "occluded", "reason"
                })
                self.assertIs(result["feasible"], expected)
                self.assertAlmostEqual(
                    result["horizontal_distance"],
                    math.dist(vehicle, target[:2]),
                )
                self.assertIsInstance(result["reason"], str)
                if expected:
                    self.assertAlmostEqual(result["horizontal_distance"], 5.0)
                    self.assertAlmostEqual(result["elevation_angle"], 45.0)
                    self.assertIs(result["occluded"], False)
                    self.assertEqual(result["reason"], "")
                else:
                    self.assertTrue(result["reason"])

    def test_empty_buildings_and_default_buildings(self):
        vehicle = (28.0, 21.0)
        target = (40.0, 21.0, CAMERA_HEIGHT)
        self.assertTrue(check_observation_feasibility(vehicle, target, [])["feasible"])
        default = check_observation_feasibility(vehicle, target)
        self.assertFalse(default["feasible"])
        self.assertTrue(default["occluded"])

    def test_combined_reasons_and_building_contact(self):
        result = check_observation_feasibility((1.0, 21.0), (22.0, 21.0, CAMERA_HEIGHT), BUILDINGS)
        self.assertFalse(result["feasible"])
        self.assertTrue(result["occluded"])
        self.assertIn("车辆", result["reason"])
        self.assertIn("遮挡", result["reason"])

    def test_gimbal_angles_near_limits(self):
        # 用角度上下相邻的坐标检查闭区间；精确等号由基础函数测试覆盖。
        for angle, expected in ((-10.01, False), (-9.99, True),
                                (79.99, True), (80.01, False)):
            with self.subTest(angle=angle):
                target = (15.0, 10.0, CAMERA_HEIGHT + 5.0 * math.tan(math.radians(angle)))
                self.assertIs(check_observation_feasibility((10.0, 10.0), target, [])["feasible"], expected)
