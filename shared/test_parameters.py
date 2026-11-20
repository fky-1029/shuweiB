"""
参数一致性测试 - 确保 constants.py 与题目 PDF 完全一致
防止参数被意外修改或恢复到错误值
"""

import math
from constants import (
    BUILDINGS, INITIAL_VEHICLE_POSITIONS, DISPATCH_CENTER,
    TARGETS, TARGETS_POLAR
)


def test_buildings():
    """测试建筑物参数"""
    print("=" * 50)
    print("建筑物参数测试")
    print("=" * 50)

    expected = [
        {'id': 1, 'x_min': 22.0, 'y_min': 16.0, 'x_max': 34.0, 'y_max': 26.0, 'height': 20.0},
        {'id': 2, 'x_min': 63.0, 'y_min': 59.0, 'x_max': 79.0, 'y_max': 71.0, 'height': 28.0},
        {'id': 3, 'x_min': 10.0, 'y_min': 65.0, 'x_max': 24.0, 'y_max': 76.0, 'height': 12.0},
        {'id': 4, 'x_min': 72.0, 'y_min': 22.0, 'x_max': 86.0, 'y_max': 34.0, 'height': 24.0},
        {'id': 5, 'x_min': 41.0, 'y_min': 38.0, 'x_max': 51.0, 'y_max': 46.0, 'height': 32.0},
    ]

    for i, (actual, expect) in enumerate(zip(BUILDINGS, expected)):
        if actual != expect:
            print(f"✗ B{i+1} 参数错误！")
            print(f"  期望: {expect}")
            print(f"  实际: {actual}")
            return False
        else:
            print(f"✓ B{i+1}: x∈[{actual['x_min']},{actual['x_max']}], "
                  f"y∈[{actual['y_min']},{actual['y_max']}], h={actual['height']}m")

    print("✓ 所有建筑物参数正确")
    return True


def test_vehicles():
    """测试车辆初始位置"""
    print("\n" + "=" * 50)
    print("车辆初始位置测试")
    print("=" * 50)

    expected = [
        {'id': 1, 'x': 15.0, 'y': 14.0},
        {'id': 2, 'x': 88.0, 'y': 10.0},
        {'id': 3, 'x': 14.0, 'y': 86.0},
        {'id': 4, 'x': 88.0, 'y': 68.0},
        {'id': 5, 'x': 50.0, 'y': 93.0},
    ]

    for i, (actual, expect) in enumerate(zip(INITIAL_VEHICLE_POSITIONS, expected)):
        if actual != expect:
            print(f"✗ V{i+1} 位置错误！")
            print(f"  期望: {expect}")
            print(f"  实际: {actual}")
            return False
        else:
            print(f"✓ V{i+1}: ({actual['x']}, {actual['y']})")

    print("✓ 所有车辆位置正确")
    return True


def test_dispatch_center():
    """测试调度中心"""
    print("\n" + "=" * 50)
    print("调度中心测试")
    print("=" * 50)

    expected = {'x': 50.0, 'y': 50.0}

    if DISPATCH_CENTER != expected:
        print(f"✗ 调度中心错误！")
        print(f"  期望: {expected}")
        print(f"  实际: {DISPATCH_CENTER}")
        return False

    print(f"✓ 调度中心: ({DISPATCH_CENTER['x']}, {DISPATCH_CENTER['y']})")
    return True


def test_targets_polar():
    """测试目标极坐标参数"""
    print("\n" + "=" * 50)
    print("目标极坐标参数测试")
    print("=" * 50)

    expected = [
        {'id': 1, 'azimuth': 30.0, 'horizontal_distance': 40.0, 'altitude': 45.0},
        {'id': 2, 'azimuth': 150.0, 'horizontal_distance': 45.0, 'altitude': 35.0},
        {'id': 3, 'azimuth': 285.0, 'horizontal_distance': 38.0, 'altitude': 55.0},
    ]

    for i, (actual, expect) in enumerate(zip(TARGETS_POLAR, expected)):
        if actual != expect:
            print(f"✗ T{i+1} 极坐标参数错误！")
            print(f"  期望: {expect}")
            print(f"  实际: {actual}")
            return False
        else:
            print(f"✓ T{i+1}: 方位角={actual['azimuth']}°, "
                  f"水平距离={actual['horizontal_distance']}m, "
                  f"高度={actual['altitude']}m")

    print("✓ 所有目标极坐标参数正确")
    return True


def test_targets_cartesian():
    """测试目标笛卡尔坐标转换"""
    print("\n" + "=" * 50)
    print("目标笛卡尔坐标转换测试")
    print("=" * 50)

    # ⚠️ 待人工确认：PDF 未明确方位角定义
    # 当前采用：x = 50 + R*cos(θ), y = 50 + R*sin(θ)
    # 期望坐标根据此公式计算

    for i, (target, polar) in enumerate(zip(TARGETS, TARGETS_POLAR)):
        # 验证极坐标参数一致性
        if target['azimuth'] != polar['azimuth'] or \
           target['horizontal_distance'] != polar['horizontal_distance'] or \
           target['z'] != polar['altitude']:
            print(f"✗ T{i+1} 极坐标与笛卡尔坐标不一致！")
            return False

        # 验证坐标转换公式：x = 50 + R*cos(θ), y = 50 + R*sin(θ)
        azimuth_rad = math.radians(polar['azimuth'])
        expected_x = 50.0 + polar['horizontal_distance'] * math.cos(azimuth_rad)
        expected_y = 50.0 + polar['horizontal_distance'] * math.sin(azimuth_rad)

        if abs(target['x'] - expected_x) > 1e-9 or abs(target['y'] - expected_y) > 1e-9:
            print(f"✗ T{i+1} 坐标转换错误！")
            print(f"  期望: x={expected_x:.6f}, y={expected_y:.6f}")
            print(f"  实际: x={target['x']:.6f}, y={target['y']:.6f}")
            return False

        print(f"✓ T{i+1}: ({target['x']:.2f}, {target['y']:.2f}, {target['z']:.2f})")

    print("⚠️  注意：方位角定义需人工确认（PDF 未明确说明）")
    print("✓ 所有目标坐标转换公式一致")
    return True


def test_no_velocity():
    """确认目标无运动速度参数"""
    print("\n" + "=" * 50)
    print("目标静止性测试")
    print("=" * 50)

    for i, target in enumerate(TARGETS):
        if 'velocity' in target or 'speed' in target:
            print(f"✗ T{i+1} 错误包含速度参数！")
            print(f"  题目规定：部署阶段目标视为静止")
            return False

    print("✓ 所有目标均无速度参数（符合题目要求）")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("参数一致性测试 - 基于 problem_B.pdf")
    print("=" * 50 + "\n")

    success = True

    success &= test_buildings()
    success &= test_vehicles()
    success &= test_dispatch_center()
    success &= test_targets_polar()
    success &= test_targets_cartesian()
    success &= test_no_velocity()

    print("\n" + "=" * 50)
    if success:
        print("🎉 所有参数一致性测试通过")
        print("=" * 50)
        exit(0)
    else:
        print("❌ 参数测试失败，请检查 constants.py")
        print("=" * 50)
        exit(1)
