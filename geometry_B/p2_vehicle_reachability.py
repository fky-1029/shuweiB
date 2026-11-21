"""P2(1) 车辆到 T2 可观测网格点的行驶时间必要条件与直达证据。

运行：.venv/bin/python -m geometry_B.p2_vehicle_reachability
不规划绕障路径，不搜索最优站位；受阻直线不证明绕行不可达。
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
import math
from pathlib import Path

from shared.constants import (
    BUILDINGS, FIELD_SIZE, INITIAL_VEHICLE_POSITIONS, VEHICLE_RADIUS,
    VEHICLE_SPEED, get_observable_points,
)
from shared.geometry_interface import is_vehicle_position_valid

MAX_TRAVEL_TIME_S = 30.0
MAX_PATH_LENGTH_M = VEHICLE_SPEED * MAX_TRAVEL_TIME_S
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "figures"
CONFIRMED_REACHABLE = "confirmed_reachable"
CONFIRMED_UNREACHABLE = "confirmed_unreachable"
PATH_UNVERIFIED = "path_unverified"


def _point(point: tuple[float, float]) -> tuple[float, float]:
    try:
        x, y = (float(value) for value in point)
    except (TypeError, ValueError) as exc:
        raise ValueError("站位必须包含两个有限坐标") from exc
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError("站位必须包含两个有限坐标")
    return x, y


def _point_to_building_distance_squared(
    start: tuple[float, float], end: tuple[float, float], building: dict,
) -> float:
    """解析求线段到闭合轴对齐矩形的最小平方距离（无离散采样）。

    按穿越矩形四条支撑直线的参数切分线段；每段到矩形的距离平方
    是一个二次式，故仅需检查区间端点与区间内驻点。
    """
    x0, y0 = start
    dx, dy = end[0] - x0, end[1] - y0
    cuts = [0.0, 1.0]
    for origin, delta, lower, upper in (
        (x0, dx, building["x_min"], building["x_max"]),
        (y0, dy, building["y_min"], building["y_max"]),
    ):
        if delta:
            cuts.extend(t for bound in (lower, upper)
                        if 0.0 < (t := (bound - origin) / delta) < 1.0)
    cuts.sort()

    def squared(t: float) -> float:
        x, y = x0 + dx * t, y0 + dy * t
        gap_x = x - min(max(x, building["x_min"]), building["x_max"])
        gap_y = y - min(max(y, building["y_min"]), building["y_max"])
        return gap_x * gap_x + gap_y * gap_y

    best = math.inf
    for left, right in zip(cuts, cuts[1:]):
        mid = (left + right) / 2.0
        x, y = x0 + dx * mid, y0 + dy * mid
        # Within each interval, each axis contributes either zero or
        # (origin + delta*t - nearest rectangle boundary)^2.
        bx = min(max(x, building["x_min"]), building["x_max"])
        by = min(max(y, building["y_min"]), building["y_max"])
        ax = dx if x != bx else 0.0
        ay = dy if y != by else 0.0
        cx = x0 - bx if ax else 0.0
        cy = y0 - by if ay else 0.0
        denom = ax * ax + ay * ay
        best = min(best, squared(left), squared(right))
        if denom:
            stationary = -(ax * cx + ay * cy) / denom
            best = min(best, squared(min(right, max(left, stationary))))
    return best


def straight_path_is_legal(
    start: tuple[float, float], end: tuple[float, float],
    *, buildings: list[dict] | None = None,
    field_size: float = FIELD_SIZE, vehicle_radius: float = VEHICLE_RADIUS,
) -> bool:
    """连续检验车中心整条直线的圆盘边界与建筑碰撞；相切允许。

    对凸方形场地，端点圆盘合法即保证线段沿途不越界。建筑采用
    线段至矩形的最小欧氏距离而非外扩包围盒或点采样。
    """
    start, end = _point(start), _point(end)
    active = BUILDINGS if buildings is None else buildings
    if not is_vehicle_position_valid(start, active, field_size, vehicle_radius):
        return False
    if not is_vehicle_position_valid(end, active, field_size, vehicle_radius):
        return False
    # 与共享站位合法性接口的 1e-12 m 接触容差一致。
    clearance = max(0.0, vehicle_radius - 1e-12)
    return all(_point_to_building_distance_squared(start, end, building) >= clearance**2
               for building in active)


@dataclass(frozen=True)
class Reachability:
    vehicle_id: int
    station: tuple[float, float]
    euclidean_distance_m: float
    passes_distance_screen: bool
    status: str
    path_length_m: float | None
    travel_time_s: float | None
    evidence: str

    @property
    def confirmed_reachable(self) -> bool:
        return self.status == CONFIRMED_REACHABLE


def assess_station(
    vehicle_id: int, start: tuple[float, float], station: tuple[float, float],
    *, buildings: list[dict] | None = None,
    field_size: float = FIELD_SIZE, vehicle_radius: float = VEHICLE_RADIUS,
    speed: float = VEHICLE_SPEED, time_limit: float = MAX_TRAVEL_TIME_S,
) -> Reachability:
    """分类一个站位。未验证绕行的点绝不赋实际行驶时间。"""
    start, station = _point(start), _point(station)
    if not (math.isfinite(speed) and speed > 0 and
            math.isfinite(time_limit) and time_limit >= 0):
        raise ValueError("车速与时限必须是有效非负参数，车速须大于零")
    distance = math.dist(start, station)
    limit = speed * time_limit
    if distance > limit:
        return Reachability(vehicle_id, station, distance, False,
                            CONFIRMED_UNREACHABLE, None, None,
                            "欧氏距离超过最大合法路径长度（严格下界）")
    if straight_path_is_legal(start, station, buildings=buildings,
                              field_size=field_size, vehicle_radius=vehicle_radius):
        return Reachability(vehicle_id, station, distance, True,
                            CONFIRMED_REACHABLE, distance, distance / speed,
                            "圆盘连续直线路径合法；长度达到欧氏距离下界")
    return Reachability(vehicle_id, station, distance, True,
                        PATH_UNVERIFIED, None, None,
                        "直线受阻；未验证是否存在满足时限的合法绕行路径")


class ReachabilityIndex:
    """以 (车号, 网格站位) 查询确认状态、行驶时间及必要条件。"""

    def __init__(self, points: tuple[tuple[float, float], ...],
                 vehicles: list[dict] | None = None):
        self.points = tuple(_point(p) for p in points)
        if len(set(self.points)) != len(self.points):
            raise ValueError("可观测点包含重复坐标")
        if not all(VEHICLE_RADIUS <= x <= FIELD_SIZE - VEHICLE_RADIUS and
                   VEHICLE_RADIUS <= y <= FIELD_SIZE - VEHICLE_RADIUS
                   for x, y in self.points):
            raise ValueError("可观测点超出车辆圆盘允许的场地坐标范围")
        fleet = INITIAL_VEHICLE_POSITIONS if vehicles is None else vehicles
        self.vehicles = {v["id"]: (v["x"], v["y"]) for v in fleet}
        self.records = {
            vehicle_id: {p: assess_station(vehicle_id, start, p) for p in self.points}
            for vehicle_id, start in self.vehicles.items()
        }

    def get(self, vehicle_id: int, station: tuple[float, float]) -> Reachability:
        """只查询已加载的可观测点；未知车辆或非网格站位抛 KeyError。"""
        return self.records[vehicle_id][_point(station)]

    def summary(self) -> list[dict]:
        rows = []
        for vehicle_id, records in self.records.items():
            values = tuple(records.values())
            rows.append({
                "vehicle_id": vehicle_id,
                "total_observable": len(values),
                "distance_screen_candidates": sum(v.passes_distance_screen for v in values),
                "distance_screen_excluded": sum(not v.passes_distance_screen for v in values),
                "confirmed_reachable": sum(v.status == CONFIRMED_REACHABLE for v in values),
                "path_unverified": sum(v.status == PATH_UNVERIFIED for v in values),
                "confirmed_unreachable": sum(v.status == CONFIRMED_UNREACHABLE for v in values),
            })
        return rows


def export_csv(index: ReachabilityIndex, output_dir: Path = OUTPUT_DIRECTORY) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = index.summary()
    with (output_dir / "p2_t2_reachability_summary.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    for vehicle_id, records in index.records.items():
        path = output_dir / f"p2_t2_v{vehicle_id}_distance_candidates.csv"
        with path.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("x_east_m", "y_north_m", "euclidean_distance_m",
                             "status", "path_length_m", "travel_time_s", "evidence"))
            for item in records.values():
                if item.passes_distance_screen:
                    writer.writerow((item.station[0], item.station[1],
                                     item.euclidean_distance_m, item.status,
                                     "" if item.path_length_m is None else item.path_length_m,
                                     "" if item.travel_time_s is None else item.travel_time_s,
                                     item.evidence))


def plot_comparison(index: ReachabilityIndex, output_dir: Path = OUTPUT_DIRECTORY) -> None:
    """五幅小图：灰色背景是全体可观测点，蓝色为直达已证实点。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    output_dir.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 3, figsize=(15, 10), sharex=True, sharey=True,
                                constrained_layout=True)
    axes = axes.flat
    all_x = [p[0] for p in index.points]
    all_y = [p[1] for p in index.points]
    for ax, (vehicle_id, records) in zip(axes, index.records.items()):
        ax.scatter(all_x, all_y, s=0.6, color="#c3c2b7", rasterized=True)
        confirmed = [p for p, item in records.items() if item.confirmed_reachable]
        if confirmed:
            ax.scatter([p[0] for p in confirmed], [p[1] for p in confirmed],
                       s=0.8, color="#2a78d6", rasterized=True)
        start = index.vehicles[vehicle_id]
        ax.scatter(*start, s=40, marker="x", color="#0b0b0b", linewidth=1.8)
        for b in BUILDINGS:
            ax.add_patch(Rectangle((b["x_min"], b["y_min"]),
                                   b["x_max"] - b["x_min"], b["y_max"] - b["y_min"],
                                   facecolor="#52514e", alpha=0.5, linewidth=0))
        ax.set_title(f"V{vehicle_id}  |  confirmed {len(confirmed):,}  /  {len(index.points):,}")
        ax.set_xlim(0, FIELD_SIZE)
        ax.set_ylim(0, FIELD_SIZE)
        ax.set_aspect("equal")
        ax.set_xlabel("East x (m)")
        ax.set_ylabel("North y (m)")
    axes[5].axis("off")
    axes[5].text(0.06, 0.78, "Map key", transform=axes[5].transAxes,
                 ha="left", va="center", fontsize=15, weight="bold")
    for height, mark, description in (
        (0.64, "●", "Gray: all observable grid points"),
        (0.54, "●", "Blue: certified straight route within 30 s"),
        (0.44, "×", "Black X: vehicle starting location"),
    ):
        axes[5].text(0.06, height, mark, transform=axes[5].transAxes,
                     color="#2a78d6" if height == 0.54 else "#52514e",
                     fontsize=14, ha="left", va="center")
        axes[5].text(0.13, height, description, transform=axes[5].transAxes,
                     color="#0b0b0b", fontsize=10, ha="left", va="center")
    axes[5].text(0.06, 0.26,
                 "Gray does not mean unreachable.\n"
                 "For excluded points and unverified detours,\n"
                 "consult the per-vehicle CSV and summary table.",
                 transform=axes[5].transAxes, color="#52514e",
                 fontsize=10, ha="left", va="center")
    figure.suptitle("T2 observable stations and certified straight-path reachability")
    with (output_dir / "p2_t2_vehicle_reachability_v2.png").open("xb") as stream:
        figure.savefig(stream, format="png", dpi=180)
    plt.close(figure)


def main() -> list[dict]:
    points = get_observable_points("T2")
    index = ReachabilityIndex(points)
    export_csv(index)
    plot_comparison(index)
    return index.summary()


if __name__ == "__main__":
    for row in main():
        print(row)
