"""
基础几何函数测试 - 测试距离和仰角计算
不包含建筑遮挡测试（P1 核心算法，待独立设计）
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from constants import CAMERA_HEIGHT, GIMBAL_PITCH_MIN, GIMBAL_PITCH_MAX
from geometry_interface import (
    calculate_horizontal_distance,
    calculate_elevation_angle,
    is_within_gimbal_range
)


def test_horizontal_distance():
    """测试水平距离计算"""
    print("=" * 50)
    print("水平距离计算测试")
    print("=" * 50)

    test_cases = [
        # (车辆位置, 目标位置, 期望距离, 描述)
        ((0.0, 0.0), (3.0, 4.0, 0.0), 5.0, "3-4-5 直角三角形"),
        ((50.0, 50.0), (50.0, 50.0, 100.0), 0.0, "正上方（距离为0）"),
        ((0.0, 0.0), (100.0, 0.0, 0.0), 100.0, "沿x轴"),
        ((0.0, 0.0), (0.0, 100.0, 0.0), 100.0, "沿y轴"),
        ((15.0, 14.0), (84.64, 70.00, 45.0),
         math.sqrt((84.64-15.0)**2 + (70.00-14.0)**2), "车辆1到目标1"),
    ]

    success = True
    for vehicle_pos, target_pos, expected, desc in test_cases:
        try:
            result = calculate_horizontal_distance(vehicle_pos, target_pos)
            error = abs(result - expected)

            if error < 1e-6:
                print(f"✓ {desc}: {result:.2f}m")
            else:
                print(f"✗ {desc} 错误！")
                print(f"  期望: {expected:.6f}m")
                print(f"  实际: {result:.6f}m")
                print(f"  误差: {error:.6f}m")
                success = False
        except NotImplementedError:
            print(f"⚠ {desc}: 函数尚未实现")
            return False

    if success:
        print("✓ 所有水平距离测试通过")
    return success


def test_elevation_angle():
    """测试仰角计算"""
    print("\n" + "=" * 50)
    print("仰角计算测试")
    print("=" * 50)

    test_cases = [
        # (车辆位置, 目标位置, 期望仰角, 描述)
        ((0.0, 0.0), (0.0, 0.0, 2.0), 0.0, "与摄像头等高（0°）"),
        ((0.0, 0.0), (0.0, 0.0, 12.0), 90.0, "正上方（90°）"),
        ((0.0, 0.0), (10.0, 0.0, 2.0 + 10.0), 45.0, "45°仰角"),
        ((0.0, 0.0), (10.0, 0.0, 2.0), 0.0, "水平（0°）"),
        ((50.0, 50.0), (50.0, 50.0, 52.0), 90.0, "调度中心正上方"),
    ]

    success = True
    for vehicle_pos, target_pos, expected, desc in test_cases:
        try:
            result = calculate_elevation_angle(vehicle_pos, target_pos)
            error = abs(result - expected)

            if error < 1e-6:
                print(f"✓ {desc}: {result:.2f}°")
            else:
                print(f"✗ {desc} 错误！")
                print(f"  期望: {expected:.6f}°")
                print(f"  实际: {result:.6f}°")
                print(f"  误差: {error:.6f}°")
                success = False
        except NotImplementedError:
            print(f"⚠ {desc}: 函数尚未实现")
            return False

    if success:
        print("✓ 所有仰角测试通过")
    return success


def test_gimbal_range():
    """测试云台角度范围检查"""
    print("\n" + "=" * 50)
    print("云台角度范围测试")
    print("=" * 50)

    test_cases = [
        (-10.0, True, "最小角度 -10°"),
        (80.0, True, "最大角度 80°"),
        (0.0, True, "水平 0°"),
        (45.0, True, "正常角度 45°"),
        (-15.0, False, "超出下限 -15°"),
        (85.0, False, "超出上限 85°"),
        (-10.1, False, "略超下限 -10.1°"),
        (80.1, False, "略超上限 80.1°"),
    ]

    success = True
    for angle, expected, desc in test_cases:
        result = is_within_gimbal_range(angle)

        if result == expected:
            status = "允许" if result else "禁止"
            print(f"✓ {desc}: {status}")
        else:
            print(f"✗ {desc} 错误！")
            print(f"  期望: {expected}")
            print(f"  实际: {result}")
            success = False

    if success:
        print("✓ 所有云台范围测试通过")
    return success


def test_realistic_scenarios():
    """测试实际场景"""
    print("\n" + "=" * 50)
    print("实际场景测试")
    print("=" * 50)

    # 车辆1 (15, 14) 到目标1 (84.64, 70.00, 45)
    vehicle_pos = (15.0, 14.0)
    target_pos = (84.64, 70.00, 45.0)

    try:
        h_dist = calculate_horizontal_distance(vehicle_pos, target_pos)
        angle = calculate_elevation_angle(vehicle_pos, target_pos)
        in_range = is_within_gimbal_range(angle)

        print(f"车辆1 → 目标1:")
        print(f"  水平距离: {h_dist:.2f}m")
        print(f"  仰角: {angle:.2f}°")
        print(f"  云台范围: {'✓ 可用' if in_range else '✗ 超限'}")

        # 计算预期值进行验证
        expected_h_dist = math.sqrt((84.64-15.0)**2 + (70.00-14.0)**2)
        camera_height = 2.0
        delta_h = 45.0 - camera_height
        expected_angle = math.degrees(math.atan2(delta_h, expected_h_dist))

        h_error = abs(h_dist - expected_h_dist)
        a_error = abs(angle - expected_angle)

        if h_error < 1e-6 and a_error < 1e-6:
            print("✓ 实际场景计算正确")
            return True
        else:
            print(f"✗ 实际场景计算错误")
            print(f"  水平距离误差: {h_error:.6f}m")
            print(f"  仰角误差: {a_error:.6f}°")
            return False

    except NotImplementedError:
        print("⚠ 函数尚未实现，无法测试实际场景")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("基础几何函数测试")
    print("=" * 50 + "\n")

    success = True

    success &= test_gimbal_range()  # 已实现的函数
    success &= test_horizontal_distance()  # 待实现
    success &= test_elevation_angle()  # 待实现
    success &= test_realistic_scenarios()  # 综合测试

    print("\n" + "=" * 50)
    if success:
        print("🎉 所有基础几何测试通过")
        print("=" * 50)
        exit(0)
    else:
        print("❌ 部分测试失败")
        print("=" * 50)
        exit(1)
