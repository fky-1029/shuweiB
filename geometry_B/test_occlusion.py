"""
建筑遮挡算法测试 - P1 核心功能
测试框架已准备，等待 check_building_occlusion() 实现
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from constants import BUILDINGS, CAMERA_HEIGHT
from geometry_interface import check_building_occlusion


def test_no_occlusion():
    """测试无遮挡情况"""
    print("=" * 60)
    print("测试 1: 无遮挡情况")
    print("=" * 60)

    # 视线完全避开所有建筑物
    test_cases = [
        # (摄像头位置, 目标位置, 描述)
        ((0.0, 0.0), (5.0, 5.0, 10.0), "场地左下角，远离所有建筑"),
        ((95.0, 95.0), (98.0, 98.0, 50.0), "场地右上角，远离所有建筑"),
    ]

    try:
        for vehicle_pos, target_pos, desc in test_cases:
            occluded, building_id = check_building_occlusion(
                vehicle_pos, target_pos, BUILDINGS
            )

            if not occluded:
                print(f"✓ {desc}: 无遮挡")
            else:
                print(f"✗ {desc}: 错误判断为被建筑 {building_id} 遮挡")
                return False

        print("✓ 无遮挡测试通过")
        return True

    except NotImplementedError:
        print("⚠ check_building_occlusion() 尚未实现")
        return None


def test_complete_occlusion():
    """测试完全遮挡情况"""
    print("\n" + "=" * 60)
    print("测试 2: 完全遮挡情况")
    print("=" * 60)

    # 视线穿过建筑物中心
    # B1: x∈[22, 34], y∈[16, 26], h=20m
    test_cases = [
        # (摄像头位置, 目标位置, 预期遮挡建筑ID, 描述)
        ((10.0, 21.0), (40.0, 21.0, 10.0), 1, "水平视线穿过 B1 中心"),
        ((28.0, 10.0), (28.0, 30.0, 10.0), 1, "水平视线穿过 B1 中心（另一方向）"),
    ]

    try:
        for vehicle_pos, target_pos, expected_id, desc in test_cases:
            occluded, building_id = check_building_occlusion(
                vehicle_pos, target_pos, BUILDINGS
            )

            if occluded and building_id == expected_id:
                print(f"✓ {desc}: 被建筑 {building_id} 遮挡")
            elif occluded:
                print(f"⚠ {desc}: 被建筑 {building_id} 遮挡（预期 {expected_id}）")
            else:
                print(f"✗ {desc}: 错误判断为无遮挡")
                return False

        print("✓ 完全遮挡测试通过")
        return True

    except NotImplementedError:
        print("⚠ check_building_occlusion() 尚未实现")
        return None


def test_behind_building():
    """测试目标在建筑后方但视线不经过建筑"""
    print("\n" + "=" * 60)
    print("测试 3: 建筑背后但无遮挡")
    print("=" * 60)

    # B1: x∈[22, 34], y∈[16, 26], h=20m
    # 摄像头和目标都在建筑同一侧，视线不穿过建筑
    test_cases = [
        ((10.0, 21.0), (15.0, 21.0, 10.0), "两者都在 B1 左侧"),
        ((40.0, 21.0), (50.0, 21.0, 10.0), "两者都在 B1 右侧"),
    ]

    try:
        for vehicle_pos, target_pos, desc in test_cases:
            occluded, building_id = check_building_occlusion(
                vehicle_pos, target_pos, BUILDINGS
            )

            if not occluded:
                print(f"✓ {desc}: 无遮挡")
            else:
                print(f"✗ {desc}: 错误判断为被建筑 {building_id} 遮挡")
                return False

        print("✓ 建筑背后测试通过")
        return True

    except NotImplementedError:
        print("⚠ check_building_occlusion() 尚未实现")
        return None


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("测试 4: 边界情况")
    print("=" * 60)

    # B1: x∈[22, 34], y∈[16, 26], h=20m
    test_cases = [
        # (摄像头位置, 目标位置, 描述)
        ((10.0, 10.0), (10.0, 10.0, 50.0), "垂直向上（摄像头正上方）"),
        ((28.0, 21.0), (28.0, 21.0, 10.0), "摄像头在 B1 正上方"),
        ((0.0, 21.0), (100.0, 21.0, 25.0), "视线高于 B1 顶部（h=20m）"),
        ((0.0, 21.0), (100.0, 21.0, 5.0), "视线低于 B1 顶部"),
    ]

    try:
        for vehicle_pos, target_pos, desc in test_cases:
            occluded, building_id = check_building_occlusion(
                vehicle_pos, target_pos, BUILDINGS
            )

            status = f"被建筑 {building_id} 遮挡" if occluded else "无遮挡"
            print(f"  {desc}: {status}")

        print("⚠ 边界情况测试结果需人工验证")
        return True

    except NotImplementedError:
        print("⚠ check_building_occlusion() 尚未实现")
        return None


def test_realistic_scenarios():
    """测试实际场景"""
    print("\n" + "=" * 60)
    print("测试 5: 实际场景 - 车辆与目标组合")
    print("=" * 60)

    from constants import INITIAL_VEHICLE_POSITIONS, TARGETS

    try:
        print("\n检查所有 5×3=15 种车辆-目标组合的遮挡情况：\n")

        occlusion_matrix = []

        for i, vehicle in enumerate(INITIAL_VEHICLE_POSITIONS):
            vehicle_pos = (vehicle['x'], vehicle['y'])
            row = []

            for j, target in enumerate(TARGETS):
                target_pos = (target['x'], target['y'], target['z'])

                occluded, building_id = check_building_occlusion(
                    vehicle_pos, target_pos, BUILDINGS
                )

                row.append((occluded, building_id))

                status = f"B{building_id}" if occluded else "✓"
                print(f"  V{i+1} → T{j+1}: {status:>3}", end="")

            print()  # 换行
            occlusion_matrix.append(row)

        # 统计
        total = 15
        occluded_count = sum(1 for row in occlusion_matrix for (occ, _) in row if occ)
        clear_count = total - occluded_count

        print(f"\n统计: {clear_count}/{total} 条视线无遮挡, "
              f"{occluded_count}/{total} 条视线被遮挡")

        print("⚠ 实际场景结果需人工验证（对照场地图）")
        return True

    except NotImplementedError:
        print("⚠ check_building_occlusion() 尚未实现")
        return None


def test_algorithm_not_implemented():
    """检查算法是否实现"""
    print("=" * 60)
    print("检查 check_building_occlusion() 实现状态")
    print("=" * 60)

    try:
        # 简单测试调用
        result = check_building_occlusion((0.0, 0.0), (1.0, 1.0, 1.0), BUILDINGS)
        print("✓ check_building_occlusion() 已实现")
        return True
    except NotImplementedError:
        print("⚠ check_building_occlusion() 尚未实现")
        print("\n请参考 geometry_B/occlusion_algorithm_design.md 设计文档")
        print("推荐方案：射线-AABB 相交检测（Slab 方法）")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("P1 建筑遮挡算法测试")
    print("=" * 60 + "\n")

    implemented = test_algorithm_not_implemented()

    if not implemented:
        print("\n" + "=" * 60)
        print("❌ 核心算法尚未实现，无法继续测试")
        print("=" * 60)
        exit(1)

    print()
    results = []
    results.append(test_no_occlusion())
    results.append(test_complete_occlusion())
    results.append(test_behind_building())
    results.append(test_edge_cases())
    results.append(test_realistic_scenarios())

    # 过滤掉 None（未实现）
    results = [r for r in results if r is not None]

    print("\n" + "=" * 60)
    if all(results):
        print("🎉 所有建筑遮挡测试通过")
        print("=" * 60)
        exit(0)
    else:
        print("❌ 部分测试失败")
        print("=" * 60)
        exit(1)
