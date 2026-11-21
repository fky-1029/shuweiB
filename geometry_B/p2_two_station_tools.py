"""P2(1) 双站的基础几何与空结果表；不实现定位精度模型或选站优化。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Callable

Point2 = tuple[float, float]
TravelTime = Callable[[Point2, Point2], float]


def _point(point: Point2) -> Point2:
    if len(point) != 2 or not all(math.isfinite(v) for v in point):
        raise ValueError("坐标必须是两个有限实数（米）")
    return point


def distance_2d(first: Point2, second: Point2) -> float:
    """两平面坐标间的直线欧氏距离（米）；非绕建筑行驶路径距离。"""
    x1, y1 = _point(first)
    x2, y2 = _point(second)
    return math.hypot(x2 - x1, y2 - y1)


def target_ranges(target_xy: Point2, station_a: Point2, station_b: Point2) -> tuple[float, float]:
    """目标到两站的水平距离（米），不使用目标高度。"""
    return distance_2d(target_xy, station_a), distance_2d(target_xy, station_b)


def intersection_angle_deg(target_xy: Point2, station_a: Point2, station_b: Point2) -> float:
    """以目标为顶点的两条观测线夹角 [0,180]（度）。

    站位与目标重合时方位未定义，抛出 ValueError；共线允许返回 0 或 180，
    病态精度处理留给队员决定，不能自行裁剪或替代核心数学模型。
    """
    tx, ty = _point(target_xy)
    ax, ay = _point(station_a)
    bx, by = _point(station_b)
    ux, uy, vx, vy = ax - tx, ay - ty, bx - tx, by - ty
    if math.hypot(ux, uy) == 0 or math.hypot(vx, vy) == 0:
        raise ValueError("站位与目标重合，交会角未定义")
    return math.degrees(math.atan2(abs(ux * vy - uy * vx), ux * vx + uy * vy))


def straight_line_travel_time(initial_xy: Point2, station_xy: Point2, speed_m_per_s: float) -> float:
    """仅给出距离/速度的直线时间参考，不代表避障后的实际行驶时间。"""
    if not math.isfinite(speed_m_per_s) or speed_m_per_s <= 0:
        raise ValueError("速度必须是正的有限值（m/s）")
    return distance_2d(initial_xy, station_xy) / speed_m_per_s


@dataclass(frozen=True)
class TwoStationResultRow:
    """P2(1) 待填结果行；精度与行驶时间均由后续已确认的方法提供。"""

    vehicle_a_id: str
    vehicle_b_id: str
    station_a_x_m: float
    station_a_y_m: float
    station_b_x_m: float
    station_b_y_m: float
    baseline_m: float | None = None
    intersection_angle_deg: float | None = None
    vehicle_a_travel_time_s: float | None = None
    vehicle_b_travel_time_s: float | None = None
    accuracy_metric_name: str | None = None
    accuracy_metric_value: float | None = None
    accuracy_metric_unit: str | None = None

    def as_csv_row(self) -> dict:
        return asdict(self)
