"""P1 理论最优半径圆周离散候选、直线时间下界和独立的安全净空诊断。

不修改综合几何约束，不实现避障路径；运行 .venv/bin/python -m geometry_B.p1_circle_analysis
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from geometry_B.observable_region_plot import plot_field
from geometry_B.figure_style import COLORS, apply_figure_style
from shared.constants import (
    BUILDINGS, CAMERA_HEIGHT, FIELD_SIZE, GIMBAL_PITCH_MAX, TARGETS,
    VEHICLE_RADIUS, VEHICLE_SPEED, INITIAL_VEHICLE_POSITIONS,
)
from shared.geometry_interface import (
    calculate_elevation_angle, calculate_horizontal_distance,
    check_observation_feasibility, is_vehicle_position_valid,
    check_building_occlusion, is_within_gimbal_range,
)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
T1 = TARGETS[0]
TARGET = (T1["x"], T1["y"], T1["z"])
R_STAR = (T1["z"] - CAMERA_HEIGHT) / math.tan(math.radians(GIMBAL_PITCH_MAX))
# 仅允许微小浮点舍入修正；绝不改变共享接口的闭区间约束。
ROUNDING_BUDGET_M = 1e-11
TIME_TIE_TOLERANCE_S = 1e-9  # 仅用于已有实际路径结果的数值同时间判别
KNOWN_WITNESS = (80.00207316612234, 75.99731976870402)


def sight_clearance_m(position: tuple[float, float]) -> float:
    """有限三维视线段与五建筑闭长方体的最小欧氏净距（米）。

    对每个长方体把线段参数按各轴穿过盒面的位置切分；每段上距离平方为
    分段二次凸函数，检查两端及内部驻点，不改变已有遮挡判定。
    """
    start = np.array((position[0], position[1], CAMERA_HEIGHT), dtype=float)
    delta = np.array(TARGET, dtype=float) - start
    best = math.inf
    for building in BUILDINGS:
        lower = np.array((building["x_min"], building["y_min"], 0.0))
        upper = np.array((building["x_max"], building["y_max"], building["height"]))
        cuts = [0.0, 1.0]
        for k in range(3):
            if delta[k] != 0:
                cuts.extend(t for bound in (lower[k], upper[k])
                            if 0 < (t := (bound - start[k]) / delta[k]) < 1)
        cuts = sorted(set(cuts))
        for left, right in zip(cuts[:-1], cuts[1:]):
            midpoint = (left + right) / 2
            probe = start + midpoint * delta
            below, above = probe < lower, probe > upper
            linear = np.where(below, -delta, np.where(above, delta, 0.0))
            intercept = np.where(below, lower - start, np.where(above, start - upper, 0.0))
            candidates = [left, right]
            slope_sq = float(linear @ linear)
            if slope_sq:
                candidates.append(float(np.clip(-linear @ intercept / slope_sq, left, right)))
            for t in candidates:
                pt = start + t * delta
                displacement = np.maximum(lower - pt, 0) + np.minimum(upper - pt, 0)
                best = min(best, float(np.linalg.norm(displacement)))
    return best


def parking_clearance_m(position: tuple[float, float]) -> float:
    """车体与建筑投影及场地边线的最小净空，米；可行点非负。"""
    x, y = position
    boundaries = min(x, y, FIELD_SIZE - x, FIELD_SIZE - y) - VEHICLE_RADIUS
    obstacles = []
    for b in BUILDINGS:
        dx = max(b["x_min"] - x, 0, x - b["x_max"])
        dy = max(b["y_min"] - y, 0, y - b["y_max"])
        obstacles.append(math.hypot(dx, dy) - VEHICLE_RADIUS)
    return min(boundaries, *obstacles)


def gimbal_aim_time_s(position: tuple[float, float]) -> float:
    """正东水平起步；两轴同时以最大 30°/s 转动，停车后开始。"""
    azimuth = math.degrees(math.atan2(T1["y"] - position[1], T1["x"] - position[0]))
    horizontal_turn = abs((azimuth + 180) % 360 - 180)
    elevation = calculate_elevation_angle(position, TARGET)
    return max(horizontal_turn, abs(elevation)) / 30.0


def circle_point(degrees: int) -> dict:
    """完整保留原始判定；只对纯浮点角度超限点作向外 ULP 修正。"""
    rad = math.radians(degrees)
    original = (T1["x"] + R_STAR * math.cos(rad), T1["y"] + R_STAR * math.sin(rad))
    raw = check_observation_feasibility(original, TARGET)
    raw_parking = is_vehicle_position_valid(original)
    raw_occluded, _ = check_building_occlusion(original, TARGET, BUILDINGS)
    raw_gimbal = is_within_gimbal_range(calculate_elevation_angle(original, TARGET))
    point, current = original, raw
    steps = 0
    if not raw_gimbal and raw["elevation_angle"] > GIMBAL_PITCH_MAX:
        while steps < 16 and not is_within_gimbal_range(current["elevation_angle"]):
            point = tuple(math.nextafter(v, math.inf if v >= c else -math.inf)
                          for v, c in zip(point, (T1["x"], T1["y"])))
            steps += 1
            current = check_observation_feasibility(point, TARGET)
        if (not is_within_gimbal_range(current["elevation_angle"])
                or calculate_horizontal_distance(point, TARGET) - R_STAR > ROUNDING_BUDGET_M):
            raise ArithmeticError(f"圆周角度 {degrees}° 不在可接受的浮点修正范围")
    parking = is_vehicle_position_valid(point)
    occluded, _ = check_building_occlusion(point, TARGET, BUILDINGS)
    gimbal = is_within_gimbal_range(calculate_elevation_angle(point, TARGET))
    if current["feasible"] != (parking and not occluded and gimbal):
        raise AssertionError("综合接口与分项判定不一致")
    return {
        "circle_angle_deg": degrees, "raw_x_east_m": original[0], "raw_y_north_m": original[1],
        "raw_feasible": raw["feasible"], "raw_reason": raw["reason"],
        "raw_parking_valid": raw_parking, "raw_line_of_sight_clear": not raw_occluded,
        "raw_gimbal_valid": raw_gimbal, "rounding_adjustment_steps": steps,
        "x_east_m": point[0], "y_north_m": point[1],
        "radius_deviation_m": calculate_horizontal_distance(point, TARGET) - R_STAR,
        "parking_valid": parking, "line_of_sight_clear": not occluded,
        "gimbal_valid": gimbal, "feasible": current["feasible"], "reason": current["reason"],
        "r_horizontal_m": current["horizontal_distance"],
        "theta_elevation_deg": current["elevation_angle"],
        "Q_inverse_m": 1 / current["horizontal_distance"],
        "sight_clearance_m": sight_clearance_m(point),
        "parking_clearance_m": parking_clearance_m(point),
        "gimbal_aim_time_s": gimbal_aim_time_s(point),
    }


def vehicle_positions() -> dict[str, tuple[float, float]]:
    """读取原始五车坐标；不从别处重写参数。"""
    return {f"V{v['id']}": (v["x"], v["y"]) for v in INITIAL_VEHICLE_POSITIONS}


def compare(circle: list[dict], travel_time: Callable[[tuple[float, float], tuple[float, float]], float] | None = None):
    """未注入 A 的避障行驶时间时，只计算直线行驶 + 云台指向时间下界。"""
    vehicles = vehicle_positions()
    mode = "actual_path" if travel_time is not None else "straight_line_lower_bound"
    rows = []
    for candidate in circle:
        if not candidate["feasible"]:
            continue
        position = (candidate["x_east_m"], candidate["y_north_m"])
        station_rows = []
        for name, start in vehicles.items():
            straight = math.dist(start, position)
            driving = straight / VEHICLE_SPEED if travel_time is None else travel_time(start, position)
            if not math.isfinite(driving) or driving < straight / VEHICLE_SPEED - 1e-9:
                raise ValueError("行驶时间非有限、负值或小于直线行驶下界")
            station_rows.append({"circle_angle_deg": candidate["circle_angle_deg"], "vehicle_id": name,
                         "start_x_m": start[0], "start_y_m": start[1],
                         "station_x_m": position[0], "station_y_m": position[1],
                         "straight_distance_m": straight, "driving_time_s": driving,
                         "gimbal_aim_time_s": candidate["gimbal_aim_time_s"],
                         "deployment_time_s": driving + candidate["gimbal_aim_time_s"],
                         "time_type": mode,
                         "sight_clearance_m": candidate["sight_clearance_m"],
                         "parking_clearance_m": candidate["parking_clearance_m"]})
        fastest = min(row["deployment_time_s"] for row in station_rows)
        for row in station_rows:
            row["fastest_for_station"] = row["deployment_time_s"] == fastest
        rows.extend(station_rows)
    return rows


def choose_actual_sample(comparisons: list[dict], time_tolerance_s: float = TIME_TIE_TOLERANCE_S) -> dict:
    """只对已提供真实避障行驶时间的离散样本执行分层比较。

    在有声明的时间容差内，以通视净空、停车净空依次作非加权字典序比较。
    对下界表禁用该选择，避免伪造最终部署方案。
    """
    if not comparisons or any(row["time_type"] != "actual_path" for row in comparisons):
        raise ValueError("仅允许对已确认实际路径时间的比较表选择站位")
    if not math.isfinite(time_tolerance_s) or time_tolerance_s < 0:
        raise ValueError("时间同值容差必须是非负有限秒数")
    minimum = min(row["deployment_time_s"] for row in comparisons)
    ties = [row for row in comparisons if row["deployment_time_s"] <= minimum + time_tolerance_s]
    return min(ties, key=lambda row: (-row["sight_clearance_m"],
                                      -row["parking_clearance_m"], row["circle_angle_deg"],
                                      row["vehicle_id"]))


def _write_csv(path: Path, rows: list[dict]):
    if not rows:
        raise ValueError("没有可写的行")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(travel_time: Callable[[tuple[float, float], tuple[float, float]], float] | None = None) -> dict:
    circle = [circle_point(degrees) for degrees in range(360)]
    valid = [p for p in circle if p["feasible"]]
    comparisons = compare(circle, travel_time)
    mode = "actual_path" if travel_time is not None else "straight_line_lower_bound"
    _write_csv(FIGURES / "p1_t1_circle_candidates_1deg.csv", circle)
    _write_csv(FIGURES / "p1_t1_vehicle_deployment_1deg.csv", comparisons)
    best_lower = min(comparisons, key=lambda row: row["deployment_time_s"])
    selected_sample = choose_actual_sample(comparisons) if travel_time is not None else None
    apply_figure_style()
    with np.load(FIGURES / "p1_t1_observable_grid_0p5m.npz") as grid:
        fig, ax = plot_field(observable=grid["observable"], x_values=grid["x_values"],
                        y_values=grid["y_values"])
    circle_xy = np.array([(p["x_east_m"], p["y_north_m"]) for p in circle])
    valid_xy = np.array([(p["x_east_m"], p["y_north_m"]) for p in valid])
    circle_line, = ax.plot(circle_xy[:, 0], circle_xy[:, 1], color="#ffffff", lw=0.65, zorder=6)
    feasible_scatter = ax.scatter(valid_xy[:, 0], valid_xy[:, 1], color=COLORS["feasible"], s=9,
               edgecolors="#1f2937", linewidths=0.12, zorder=7)
    screening_scatter = ax.scatter([best_lower["station_x_m"]], [best_lower["station_y_m"]],
               marker="*", c=COLORS["vehicle"], edgecolors="#333333", s=100, zorder=8)
    base_legend = ax.get_legend()
    base_handles = list(base_legend.legend_handles)
    base_labels = [text.get_text() for text in base_legend.get_texts()]
    ax.legend(base_handles + [circle_line, feasible_scatter, screening_scatter],
              base_labels + ["Theoretical radius (sampled)", "Feasible circle samples",
                             "Fastest lower-bound screen" if travel_time is None
                             else "Fastest actual-time sample"],
              loc="upper center", ncol=2, bbox_to_anchor=(.5, -.13), frameon=True)
    fig.set_size_inches(6, 4.5)
    fig.savefig(FIGURES / "p1_t1_circle_candidates_1deg.png", dpi=200, bbox_inches="tight")
    fig.savefig(FIGURES / "p1_t1_circle_candidates_1deg.svg", bbox_inches="tight")
    plt.close(fig)
    witness = check_observation_feasibility(KNOWN_WITNESS, TARGET)
    if not witness["feasible"] or abs(witness["horizontal_distance"] - R_STAR) > ROUNDING_BUDGET_M:
        raise AssertionError("给定的理论下界可行见证未通过公共接口复核")
    summary = {"target_xyz_m": list(TARGET), "radius_lower_bound_m": R_STAR,
               "known_continuous_feasible_witness_xy_m": list(KNOWN_WITNESS),
               "witness_check": witness, "sample_count": len(circle), "feasible_sample_count": len(valid),
               "raw_feasible_sample_count": sum(p["raw_feasible"] for p in circle),
               "rounding_adjusted_count": sum(p["rounding_adjustment_steps"] > 0 for p in circle),
               "max_adjustment_m": max(abs(p["radius_deviation_m"]) for p in circle),
               "time_type": mode, "comparison_count": len(comparisons),
               "best_screening_row": best_lower if travel_time is None else None,
               "selected_actual_path_sample": selected_sample,
               "time_tie_tolerance_s": TIME_TIE_TOLERANCE_S,
               "known_witness_sight_clearance_m": sight_clearance_m(KNOWN_WITNESS),
               "known_witness_parking_clearance_m": parking_clearance_m(KNOWN_WITNESS),
               "actual_path_optimum_identified": selected_sample is not None,
               "continuous_circle_deployment_optimum_proven": False,
               "note": "未提供避障路径接口时只给直线行驶+指向时间下界；圆周每 1° 扫描不能证明连续部署时间最优。"}
    (FIGURES / "p1_t1_circle_summary_1deg.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
