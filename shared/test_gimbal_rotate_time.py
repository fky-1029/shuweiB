"""云台停车后从正东水平初始姿态进行初次指向的公共接口测试。"""
import math
import unittest

from shared.constants import CAMERA_HEIGHT, GIMBAL_MAX_ANGULAR_VELOCITY
from shared.geometry_interface import calculate_elevation_angle, compute_gimbal_rotate_time


class GimbalRotateTimeTests(unittest.TestCase):
    def test_cardinal_directions(self):
        for target, pan in (
            ((10.0, 0.0, CAMERA_HEIGHT), 0.0),
            ((0.0, 10.0, CAMERA_HEIGHT), 90.0),
            ((-10.0, 0.0, CAMERA_HEIGHT), 180.0),
            ((0.0, -10.0, CAMERA_HEIGHT), 90.0),
        ):
            with self.subTest(target=target):
                t_rot, actual_pan, tilt = compute_gimbal_rotate_time((0, 0), target)
                self.assertAlmostEqual(actual_pan, pan)
                self.assertEqual(tilt, 0.0)
                self.assertAlmostEqual(t_rot, pan / GIMBAL_MAX_ANGULAR_VELOCITY)

    def test_fourth_quadrant_shortest_turn(self):
        # 285° 对应相对正东顺时针 75°，不是逆时针 285°。
        angle = math.radians(285)
        t_rot, pan, tilt = compute_gimbal_rotate_time(
            (0, 0), (10 * math.cos(angle), 10 * math.sin(angle), CAMERA_HEIGHT)
        )
        self.assertAlmostEqual(pan, 75.0)
        self.assertAlmostEqual(tilt, 0.0)
        self.assertAlmostEqual(t_rot, 75 / GIMBAL_MAX_ANGULAR_VELOCITY)

    def test_simultaneous_axes_and_existing_elevation(self):
        target = (0.0, 10.0, CAMERA_HEIGHT + 10.0)
        t_rot, pan, tilt = compute_gimbal_rotate_time((0, 0), target)
        self.assertAlmostEqual(pan, 90.0)
        self.assertAlmostEqual(tilt, 45.0)
        self.assertAlmostEqual(tilt, abs(calculate_elevation_angle((0, 0), target)))
        self.assertAlmostEqual(t_rot, 90 / GIMBAL_MAX_ANGULAR_VELOCITY)
        # 仰角轴较慢时取其完成时间；不叠加两轴时间。
        t_rot, pan, tilt = compute_gimbal_rotate_time((0, 0), (10, 0, CAMERA_HEIGHT + 10))
        self.assertEqual(pan, 0.0)
        self.assertAlmostEqual(tilt, 45.0)
        self.assertAlmostEqual(t_rot, 45 / GIMBAL_MAX_ANGULAR_VELOCITY)

    def test_each_call_starts_from_east_horizontal(self):
        compute_gimbal_rotate_time((0, 0), (-1, 0, CAMERA_HEIGHT))
        self.assertEqual(compute_gimbal_rotate_time((0, 0), (1, 0, CAMERA_HEIGHT)), (0.0, 0.0, 0.0))

    def test_invalid_and_undefined_inputs(self):
        for station, target in (
            ((0, 0), (0, 0, 45)),
            ((0,), (1, 2, 3)),
            ((0, 0), (1, 2)),
            ((float("nan"), 0), (1, 2, 3)),
            ((0, 0), (float("inf"), 2, 3)),
            (("not a number", 0), (1, 2, 3)),
        ):
            with self.subTest(station=station, target=target):
                with self.assertRaises(ValueError):
                    compute_gimbal_rotate_time(station, target)


if __name__ == "__main__":
    unittest.main()
