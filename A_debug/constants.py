"""
统一参数定义 - 数维杯 B 题
所有参数均来自题目原文，不得擅自添加未规定的限制
"""

import json
from functools import lru_cache
from pathlib import Path

# ==================== 场地参数 ====================
FIELD_SIZE = 100.0  # 场地尺寸: 100m × 100m

# ==================== 车辆参数 ====================
VEHICLE_RADIUS = 1.5  # 观测车半径: 1.5 m
VEHICLE_SPEED = 3.0  # 车辆速度: 3 m/s
CAMERA_HEIGHT = 2.0  # 摄像头高度: 2 m

# ==================== 云台参数 ====================
GIMBAL_PITCH_MIN = -10.0  # 云台最小俯仰角: -10°
GIMBAL_PITCH_MAX = 80.0  # 云台最大俯仰角: 80°
GIMBAL_MAX_ANGULAR_VELOCITY = 30.0  # 云台最大角速度: 30°/s

# ==================== 观测参数 ====================
JOINT_OBSERVATION_TIME = 5.0  # 联合观测时间: 5 s

# ==================== 建筑物参数 ====================
# 五栋建筑的平面范围 (x_min, y_min, x_max, y_max) 和高度 (单位: m)
# 来源: problem_B.pdf 第2页表格
BUILDINGS = [
    {
        'id': 1,
        'x_min': 22.0,
        'y_min': 16.0,
        'x_max': 34.0,
        'y_max': 26.0,
        'height': 20.0
    },
    {
        'id': 2,
        'x_min': 63.0,
        'y_min': 59.0,
        'x_max': 79.0,
        'y_max': 71.0,
        'height': 28.0
    },
    {
        'id': 3,
        'x_min': 10.0,
        'y_min': 65.0,
        'x_max': 24.0,
        'y_max': 76.0,
        'height': 12.0
    },
    {
        'id': 4,
        'x_min': 72.0,
        'y_min': 22.0,
        'x_max': 86.0,
        'y_max': 34.0,
        'height': 24.0
    },
    {
        'id': 5,
        'x_min': 41.0,
        'y_min': 38.0,
        'x_max': 51.0,
        'y_max': 46.0,
        'height': 32.0
    }
]

# ==================== 车辆初始位置 ====================
# 五辆车的初始二维坐标 (x, y) (单位: m)
# 来源: problem_B.pdf 第2页
INITIAL_VEHICLE_POSITIONS = [
    {'id': 1, 'x': 15.0, 'y': 14.0},
    {'id': 2, 'x': 88.0, 'y': 10.0},
    {'id': 3, 'x': 14.0, 'y': 86.0},
    {'id': 4, 'x': 88.0, 'y': 68.0},
    {'id': 5, 'x': 50.0, 'y': 93.0}
]

# ==================== 调度中心 ====================
# 调度中心坐标 (x, y) (单位: m)
# 来源: problem_B.pdf 第2页
DISPATCH_CENTER = {'x': 50.0, 'y': 50.0}

# ==================== 目标参数 ====================
# 三个无人机目标的警报参数（极坐标）和笛卡尔坐标
# 来源: problem_B.pdf 第2-3页
# 极坐标定义：相对于调度中心 (50, 50)
#   - azimuth: 方位角（度）
#   - horizontal_distance: 水平距离（m）
#   - altitude: 高度（m，离地高度）
#
# PDF 第1页规定：方位角从正东逆时针计，x 轴指东、y 轴指北
# 笛卡尔坐标转换公式：x = 50 + R*cos(θ), y = 50 + R*sin(θ)
#   其中 θ 为方位角（度，需转换为弧度）

import math

def _azimuth_to_cartesian(azimuth_deg, horizontal_distance):
    """
    将方位角转换为笛卡尔坐标

    PDF 第1-2页规定：方位角从正东逆时针计，并给出以下转换公式
    当前采用：x = 50 + R*cos(θ), y = 50 + R*sin(θ)
    """
    azimuth_rad = math.radians(azimuth_deg)
    x = 50.0 + horizontal_distance * math.cos(azimuth_rad)
    y = 50.0 + horizontal_distance * math.sin(azimuth_rad)
    return x, y

# 目标警报参数（原始极坐标形式）
TARGETS_POLAR = [
    {
        'id': 1,
        'azimuth': 30.0,              # 方位角（度）
        'horizontal_distance': 40.0,  # 水平距离（m）
        'altitude': 45.0              # 高度（m）
    },
    {
        'id': 2,
        'azimuth': 150.0,
        'horizontal_distance': 45.0,
        'altitude': 35.0
    },
    {
        'id': 3,
        'azimuth': 285.0,
        'horizontal_distance': 38.0,
        'altitude': 55.0
    }
]

# 目标笛卡尔坐标（从极坐标计算得出）
TARGETS = []
for target_polar in TARGETS_POLAR:
    x, y = _azimuth_to_cartesian(target_polar['azimuth'], target_polar['horizontal_distance'])
    TARGETS.append({
        'id': target_polar['id'],
        'x': x,
        'y': y,
        'z': target_polar['altitude'],  # 高度即为z坐标
        'azimuth': target_polar['azimuth'],
        'horizontal_distance': target_polar['horizontal_distance']
    })

# 注意：部署阶段目标视为静止，无运动速度参数


# ==================== 预计算可观测位置（工程数据）====================
def get_observable_points(target_id: str) -> tuple[tuple[float, float], ...]:
    """读取目标在 0.5 m 网格上的全部可观测车辆中心坐标。

    返回不可变坐标元组；结果按目标缓存，重复调用不会重新读取 CSV。
    相对本文件定位数据，调用方不必切换工作目录。
    """
    if target_id not in ("T1", "T2", "T3"):
        raise ValueError("target_id 必须是 T1、T2 或 T3")
    return _load_observable_points(target_id)


@lru_cache(maxsize=3)
def _load_observable_points(target_id: str) -> tuple[tuple[float, float], ...]:
    shared_json = Path(__file__).resolve().parent.parent / "shared" / "observable_points.json"
    with shared_json.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if target_id not in data:
        raise KeyError(f"共享可观测点数据中缺少 {target_id}: {shared_json}")
    return tuple((float(point[0]), float(point[1])) for point in data[target_id])
