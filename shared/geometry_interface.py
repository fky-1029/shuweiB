"""
几何检查接口 - 供调度模块调用
提供车辆对目标的可观测性判断和几何信息计算
"""

from typing import Dict, Tuple, Optional
import sys
import os

# 添加 shared 目录到路径以便导入 constants
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from constants import CAMERA_HEIGHT, GIMBAL_PITCH_MIN, GIMBAL_PITCH_MAX


def check_observation_feasibility(
    vehicle_position: Tuple[float, float],
    target_position: Tuple[float, float, float],
    buildings: Optional[list] = None
) -> Dict:
    """
    检查车辆对目标的可观测性

    参数:
        vehicle_position: 车辆中心二维坐标 (x, y) [m]
        target_position: 目标三维坐标 (x, y, z) [m]
        buildings: 建筑物列表，格式见 constants.BUILDINGS（可选）

    返回:
        dict {
            'feasible': bool,              # 是否可观测
            'horizontal_distance': float,  # 水平距离 [m]
            'elevation_angle': float,      # 云台仰角 [度]
            'occluded': bool,              # 是否被建筑遮挡
            'reason': str                  # 不可观测的原因（若不可观测）
        }

    注意:
        - 摄像头高度从 constants.CAMERA_HEIGHT 读取
        - 云台仰角范围: GIMBAL_PITCH_MIN 至 GIMBAL_PITCH_MAX
        - 本函数为接口框架，核心算法尚未实现
    """
    raise NotImplementedError(
        "check_observation_feasibility 接口尚未实现。"
        "需要实现：1) 几何距离与仰角计算；2) 建筑遮挡判断算法。"
    )


def calculate_elevation_angle(
    vehicle_position: Tuple[float, float],
    target_position: Tuple[float, float, float]
) -> float:
    """
    计算云台仰角

    参数:
        vehicle_position: 车辆中心二维坐标 (x, y) [m]
        target_position: 目标三维坐标 (x, y, z) [m]

    返回:
        float: 云台仰角 [度]，正值表示向上仰，负值表示向下俯

    注意:
        摄像头实际高度为车辆地面位置 + CAMERA_HEIGHT
    """
    import math

    # 计算水平距离
    horizontal_dist = calculate_horizontal_distance(vehicle_position, target_position)

    # 计算摄像头与目标的高度差
    camera_height = CAMERA_HEIGHT
    height_diff = target_position[2] - camera_height

    # 计算仰角（使用 atan2 处理特殊情况）
    if horizontal_dist < 1e-9:  # 目标在正上方或正下方
        if height_diff > 0:
            return 90.0
        elif height_diff < 0:
            return -90.0
        else:
            return 0.0

    elevation_angle_rad = math.atan2(height_diff, horizontal_dist)
    return math.degrees(elevation_angle_rad)


def calculate_horizontal_distance(
    vehicle_position: Tuple[float, float],
    target_position: Tuple[float, float, float]
) -> float:
    """
    计算车辆与目标的水平距离

    参数:
        vehicle_position: 车辆中心二维坐标 (x, y) [m]
        target_position: 目标三维坐标 (x, y, z) [m]

    返回:
        float: 水平距离 [m]
    """
    import math

    dx = target_position[0] - vehicle_position[0]
    dy = target_position[1] - vehicle_position[1]

    return math.sqrt(dx**2 + dy**2)


def check_building_occlusion(
    vehicle_position: Tuple[float, float],
    target_position: Tuple[float, float, float],
    buildings: list
) -> Tuple[bool, Optional[int]]:
    """
    检查视线是否被建筑物遮挡

    参数:
        vehicle_position: 车辆中心二维坐标 (x, y) [m]
        target_position: 目标三维坐标 (x, y, z) [m]
        buildings: 建筑物列表，格式见 constants.BUILDINGS

    返回:
        Tuple[bool, Optional[int]]:
            - bool: 是否被遮挡
            - int: 遮挡的建筑物 ID（若被遮挡），否则为 None

    注意:
        需要考虑三维视线与建筑物立方体的相交判断
    """
    raise NotImplementedError(
        "check_building_occlusion 尚未实现。"
        "需要实现三维射线与建筑物包围盒的相交检测算法。"
        "这是 P1 的核心几何问题，需要队员自主设计算法。"
    )


def is_within_gimbal_range(elevation_angle: float) -> bool:
    """
    检查仰角是否在云台允许范围内

    参数:
        elevation_angle: 仰角 [度]

    返回:
        bool: 是否在允许范围内
    """
    return GIMBAL_PITCH_MIN <= elevation_angle <= GIMBAL_PITCH_MAX


# ==================== 辅助函数（供内部使用）====================

def _get_camera_position(vehicle_position: Tuple[float, float]) -> Tuple[float, float, float]:
    """
    获取摄像头的三维坐标

    参数:
        vehicle_position: 车辆中心二维坐标 (x, y) [m]

    返回:
        Tuple[float, float, float]: 摄像头三维坐标 (x, y, z) [m]
    """
    return (vehicle_position[0], vehicle_position[1], CAMERA_HEIGHT)
