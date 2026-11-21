"""
几何检查接口 - 供调度模块调用
提供车辆对目标的可观测性判断和几何信息计算
"""

from typing import Dict, Tuple, Optional
import sys
import os

# 添加 shared 目录到路径以便导入 constants
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from constants import (
    BUILDINGS,
    CAMERA_HEIGHT,
    FIELD_SIZE,
    VEHICLE_RADIUS,
    GIMBAL_PITCH_MIN,
    GIMBAL_PITCH_MAX,
    GIMBAL_MAX_ANGULAR_VELOCITY,
)


def is_vehicle_position_valid(
    vehicle_position: Tuple[float, float],
    buildings: Optional[list] = None,
    field_size: float = FIELD_SIZE,
    vehicle_radius: float = VEHICLE_RADIUS,
) -> bool:
    """检查车辆圆盘是否完全位于场地内，且未侵入任何建筑。

    车辆与场地边界或建筑边界恰好接触时允许停车。建筑碰撞使用
    车辆中心到轴对齐矩形的最短欧氏距离判断，而非把建筑外扩为矩形。
    """
    import math

    if len(vehicle_position) != 2:
        raise ValueError("vehicle_position must contain exactly two coordinates")
    if not math.isfinite(field_size) or field_size <= 0:
        raise ValueError("field_size must be a positive finite number")
    if not math.isfinite(vehicle_radius) or vehicle_radius < 0:
        raise ValueError("vehicle_radius must be a non-negative finite number")

    x, y = vehicle_position
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("vehicle_position coordinates must be finite")

    # 使用闭区间判断：圆盘恰好接触场地边界时合法。
    if not (
        vehicle_radius <= x <= field_size - vehicle_radius
        and vehicle_radius <= y <= field_size - vehicle_radius
    ):
        return False

    for building in BUILDINGS if buildings is None else buildings:
        nearest_x = min(max(x, building["x_min"]), building["x_max"])
        nearest_y = min(max(y, building["y_min"]), building["y_max"])
        distance = math.hypot(x - nearest_x, y - nearest_y)
        # 给浮点计算留下极小余量，以免理论上恰好相切被误判；
        # 这并不是将建筑的几何范围外扩。
        if distance + 1e-12 < vehicle_radius:
            return False

    return True


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
        - buildings 为 None 时使用 constants.BUILDINGS；空列表表示不检查建筑
    """
    active_buildings = BUILDINGS if buildings is None else buildings
    horizontal_distance = calculate_horizontal_distance(vehicle_position, target_position)
    elevation_angle = calculate_elevation_angle(vehicle_position, target_position)
    position_valid = is_vehicle_position_valid(vehicle_position, active_buildings)
    occluded, _ = check_building_occlusion(vehicle_position, target_position, active_buildings)
    angle_valid = is_within_gimbal_range(elevation_angle)

    feasible = position_valid and not occluded and angle_valid
    reasons = []
    if not position_valid:
        reasons.append("车辆位置不合法")
    if occluded:
        reasons.append("建筑遮挡")
    if not angle_valid:
        reasons.append("云台仰角超出范围")
    return {
        "feasible": feasible,
        "horizontal_distance": horizontal_distance,
        "elevation_angle": elevation_angle,
        "occluded": occluded,
        "reason": "；".join(reasons),
    }

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


def compute_gimbal_rotate_time(
    station: tuple[float, float],
    target_pos: tuple[float, float, float],
) -> tuple[float, float, float]:
    """从正东水平初始姿态、停车后同时转动两轴的初次指向时间。

    返回 (时间 s, 最短水平转角绝对值 °, 俯仰转角绝对值 °)。
    不含行驶、观测或复位时间；若需复位，复位时长等于返回的时间。
    与目标水平投影重合时方位角无定义，抛出 ValueError。
    """
    import math

    try:
        x, y = station
        tx, ty, tz = target_pos
        x, y, tx, ty, tz = (float(v) for v in (x, y, tx, ty, tz))
    except (TypeError, ValueError) as exc:
        raise ValueError("station 应为二维坐标，target_pos 应为三维坐标") from exc
    if not all(math.isfinite(v) for v in (x, y, tx, ty, tz)):
        raise ValueError("站位和目标坐标必须为有限数值")

    dx, dy = tx - x, ty - y
    if dx == 0.0 and dy == 0.0:
        raise ValueError("目标水平投影与站位重合：水平方位角无定义")
    # atan2 返回 [-180°, 180°]，正东初始方位下取绝对值即最短转角。
    pan_angle = abs(math.degrees(math.atan2(dy, dx)))
    tilt_angle = abs(calculate_elevation_angle((x, y), (tx, ty, tz)))
    t_rot = max(pan_angle, tilt_angle) / GIMBAL_MAX_ANGULAR_VELOCITY
    return t_rot, pan_angle, tilt_angle


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
    camera = _get_camera_position(vehicle_position)

    direction = (
        target_position[0] - camera[0],
        target_position[1] - camera[1],
        target_position[2] - camera[2]
    )

    for building in buildings:
        t_min = 0.0
        t_max = 1.0
        intersects = True

        bounds_min = (
            building["x_min"],
            building["y_min"],
            0.0
        )

        bounds_max = (
            building["x_max"],
            building["y_max"],
            building["height"]
        )

        for axis in range(3):
            p = camera[axis]
            d = direction[axis]
            lower = bounds_min[axis]
            upper = bounds_max[axis]

            if abs(d) < 1e-12:
                if p < lower or p > upper:
                    intersects = False
                    break

            else:
                t1 = (lower - p) / d
                t2 = (upper - p) / d

                t_min = max(t_min, min(t1, t2))
                t_max = min(t_max, max(t1, t2))

                if t_min > t_max:
                    intersects = False
                    break

        if intersects:
            return True, building["id"]

    return False, None





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
