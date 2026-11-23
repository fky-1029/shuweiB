"""P2(1) 双站 RMSE：已证实可达网格精确搜索、待验证站位几何松弛。

运行：.venv/bin/python -m geometry_B.p2_two_station_optimize
不运行路径规划；行驶时间仅用于可行性筛选，绝不加权到 RMSE。
"""
from __future__ import annotations

import csv
from itertools import combinations
import json
import math
from pathlib import Path

import numpy as np

from geometry_B.p2_localization_accuracy import (
    DEGENERATE_SIN_THRESHOLD, calculate_localization_metrics,
)
from geometry_B.p2_vehicle_reachability import (
    CONFIRMED_REACHABLE, PATH_UNVERIFIED, MAX_TRAVEL_TIME_S, straight_path_is_legal,
)
from shared.constants import (
    BUILDINGS, FIELD_SIZE, INITIAL_VEHICLE_POSITIONS, TARGETS,
    VEHICLE_RADIUS, VEHICLE_SPEED, get_observable_points,
)
from shared.geometry_interface import check_observation_feasibility, is_vehicle_position_valid

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "figures"
TARGET = (TARGETS[1]["x"], TARGETS[1]["y"])
SIGMA_DEG = 1.0
BLOCK_SIZE = 256


def read_candidates(directory: Path = INPUT_DIR, points: tuple | None = None) -> dict[int, dict[str, dict]]:
    """读取现有可达性 CSV，交叉核对完整站位集合、距离、时间和证据。"""
    observable = set(get_observable_points("T2") if points is None else points)
    vehicles = {v["id"]: (v["x"], v["y"]) for v in INITIAL_VEHICLE_POSITIONS}
    result = {}
    for vehicle, start in vehicles.items():
        confirmed, pending, seen = {}, {}, set()
        with (directory / f"p2_t2_v{vehicle}_distance_candidates.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            reader = csv.DictReader(stream)
            required = {"x_east_m", "y_north_m", "euclidean_distance_m", "status",
                        "path_length_m", "travel_time_s"}
            if not required <= set(reader.fieldnames or ()):
                raise ValueError(f"V{vehicle} 文件列不完整")
            for row in reader:
                point = (float(row["x_east_m"]), float(row["y_north_m"]))
                if point not in observable or point in seen:
                    raise ValueError(f"V{vehicle} 非法或重复的候选站位：{point}")
                seen.add(point)
                distance = math.dist(start, point)
                if not math.isfinite(distance) or distance > VEHICLE_SPEED * MAX_TRAVEL_TIME_S or not math.isclose(
                    float(row["euclidean_distance_m"]), distance, abs_tol=1e-8
                ):
                    raise ValueError(f"V{vehicle} 距离筛选/数值不符：{point}")
                status = row["status"]
                if status == CONFIRMED_REACHABLE:
                    length, time = float(row["path_length_m"]), float(row["travel_time_s"])
                    if not (math.isclose(length, distance, abs_tol=1e-8) and
                            math.isclose(time, length / VEHICLE_SPEED, abs_tol=1e-8) and
                            time <= MAX_TRAVEL_TIME_S):
                        raise ValueError(f"V{vehicle} 直达行驶时间无效：{point}")
                    confirmed[point] = time
                elif status == PATH_UNVERIFIED:
                    if row["travel_time_s"] or row["path_length_m"]:
                        raise ValueError("未验证路径不得含确证路径长度或时间")
                    pending[point] = None
                else:
                    raise ValueError(f"不接受未知候选状态 {status}")
        expected = {p for p in observable if math.dist(start, p) <= VEHICLE_SPEED * MAX_TRAVEL_TIME_S}
        if seen != expected:
            raise ValueError(f"V{vehicle} CSV 不完整或距离边界不一致")
        result[vehicle] = {"confirmed": confirmed, "pending": pending}
    return result


def prepare(points: dict, target: tuple[float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    coords = np.asarray(list(points), dtype=np.float64).reshape((-1, 2))
    vectors = np.asarray(target, dtype=np.float64) - coords
    radii = np.hypot(vectors[:, 0], vectors[:, 1])
    # r=0 的方位角未定义，不能构成定位交会。
    return coords, vectors, radii


def search_pair(
    a: dict, b: dict, target: tuple[float, float], sigma_deg: float = SIGMA_DEG,
    *, incumbent: float = math.inf, require_pending: bool = False,
    block_size: int = BLOCK_SIZE,
) -> dict:
    """枚举全部可能改善 incumbent 的离散点对，安全剪枝而非启发式。

    sin(gamma)<=1 ⇒ RMSE>=sigma_rad*hypot(r1,r2)。只丢弃
    hypot(r1,r2)>incumbent/sigma_rad 的点对；未给有限上界时全部分块枚举。
    返回最优点对及几何更优的点对计数、参与的待验证站位集合。
    """
    if sigma_deg <= 0 or block_size <= 0:
        raise ValueError("sigma_deg 与 block_size 必须为正")
    if not (math.isinf(incumbent) or math.isfinite(incumbent)) or incumbent <= 0:
        raise ValueError("incumbent 必须为正")
    ca, va, ra = prepare(a, target)
    cb, vb, rb = prepare(b, target)
    sigma = math.radians(sigma_deg)
    best = incumbent
    best_pair = None
    if not require_pending and math.isinf(incumbent):
        # 仅构造可行上界；后续仍完整检查全部可能改善它的离散点对。
        for ii in np.linspace(0, len(ca) - 1, min(len(ca), 24), dtype=int):
            for jj in np.linspace(0, len(cb) - 1, min(len(cb), 24), dtype=int):
                if ra[ii] == 0 or rb[jj] == 0:
                    continue
                measure = calculate_localization_metrics(tuple(ca[ii]), tuple(cb[jj]), target, sigma_deg)
                if measure["rmse_m"] < best:
                    best, best_pair = measure["rmse_m"], (tuple(ca[ii]), tuple(cb[jj]))
    better_pairs = 0
    promising_a, promising_b = set(), set()
    # 若当前 incumbent 与某点对下界仅差浮点舍入量，仍保留该点对检查。
    epsilon = 1e-12
    if require_pending:
        # 只用在几何松弛：a/b 的状态字典中 True 表示尚待验证。
        pending_a = np.fromiter(a.values(), dtype=bool)
        pending_b = np.fromiter(b.values(), dtype=bool)
    else:
        pending_a = pending_b = None
    # 浮点边界略微向外扩，避免剪掉等于当前上界附近的真最优。
    radius_limit = (best / sigma) * (1 + epsilon)
    ia = np.flatnonzero((ra > 0) & (ra <= radius_limit))
    ib = np.flatnonzero((rb > 0) & (rb <= radius_limit))
    inspected = 0
    pruned = len(ca) * len(cb) - len(ia) * len(ib)
    for outer in range(0, len(ia), block_size):
        i = ia[outer:outer + block_size]
        x, y = va[i, 0][:, None], va[i, 1][:, None]
        r1 = ra[i][:, None]
        for inner in range(0, len(ib), block_size):
            j = ib[inner:inner + block_size]
            r2 = rb[j][None, :]
            radius = np.hypot(r1, r2)
            bound = incumbent if require_pending else best
            possible = sigma * radius <= bound * (1 + epsilon)
            inspected += len(i) * len(j)
            pruned += int(possible.size - np.count_nonzero(possible))
            if not np.any(possible):
                continue
            cross = x * vb[j, 1][None, :] - y * vb[j, 0][None, :]
            sine = np.abs(cross / (r1 * r2))
            valid = possible & (sine > DEGENERATE_SIN_THRESHOLD)
            if require_pending:
                valid &= pending_a[i, None] | pending_b[None, j]
            if not np.any(valid):
                continue
            scores = np.full(sine.shape, np.inf)
            np.divide(sigma * radius, sine, out=scores, where=valid)
            if require_pending:
                improve = scores < incumbent
                better_pairs += int(improve.sum())
                rows, cols = np.nonzero(improve)
                promising_a.update(tuple(ca[i[k]]) for k in np.unique(rows) if pending_a[i[k]])
                promising_b.update(tuple(cb[j[k]]) for k in np.unique(cols) if pending_b[j[k]])
            local = int(np.argmin(scores))
            value = float(scores.flat[local])
            if value < best:
                pi, pj = np.unravel_index(local, scores.shape)
                best = value
                best_pair = (tuple(ca[i[pi]]), tuple(cb[j[pj]]))
    return {"rmse_m": best if best_pair is not None else math.inf,
            "stations": best_pair, "improving_pairs": better_pairs,
            "total_pairs": len(ca) * len(cb), "pruned_by_radius_bound": pruned,
            "candidate_pairs_checked": inspected - (pruned - (len(ca) * len(cb) - len(ia) * len(ib))),
            "promising_pending_a": promising_a, "promising_pending_b": promising_b}


def make_solution(vehicles: tuple[int, int], stations: tuple, candidates: dict,
                  target: tuple[float, float] = TARGET) -> dict:
    a, b = vehicles
    p, q = stations
    metrics = calculate_localization_metrics(p, q, target)
    if metrics["degenerate"] or not math.isfinite(metrics["rmse_m"]):
        raise ValueError("不能把退化交会报告为可行解")
    return {"vehicle_a": a, "vehicle_b": b,
            "station_a": p, "station_b": q,
            "travel_time_a_s": candidates[a]["confirmed"][p],
            "travel_time_b_s": candidates[b]["confirmed"][q], **metrics}


def optimize(candidates: dict, target: tuple[float, float] = TARGET) -> tuple[list[dict], dict, list[dict]]:
    """精确求解 10 个车辆组合；再枚举几何上能改善已证实最优的待验证组合。"""
    pairs = list(combinations(sorted(candidates), 2))
    results = []
    for vehicles in pairs:
        a, b = vehicles
        answer = search_pair(candidates[a]["confirmed"], candidates[b]["confirmed"], target)
        if answer["stations"] is None:
            results.append({"vehicle_a": a, "vehicle_b": b, "rmse_m": math.inf})
        else:
            results.append(make_solution(vehicles, answer["stations"], candidates, target))
    winner = min(results, key=lambda row: row["rmse_m"])
    if not math.isfinite(winner["rmse_m"]):
        raise ValueError("已证实可达集合中不存在非退化双站方案")
    benchmark = winner["rmse_m"]
    potentials = []
    for a, b in pairs:
        a_points = {**dict.fromkeys(candidates[a]["confirmed"], False),
                    **dict.fromkeys(candidates[a]["pending"], True)}
        b_points = {**dict.fromkeys(candidates[b]["confirmed"], False),
                    **dict.fromkeys(candidates[b]["pending"], True)}
        answer = search_pair(a_points, b_points, target, incumbent=benchmark,
                             require_pending=True)
        potentials.append({"vehicle_a": a, "vehicle_b": b,
                           "geometric_better_pairs": answer["improving_pairs"],
                           "promising_pending_a": len(answer["promising_pending_a"]),
                           "promising_pending_b": len(answer["promising_pending_b"]),
                           "best_relaxed_stations": answer["stations"],
                           "best_relaxed_rmse_m": (answer["rmse_m"] if answer["stations"] is not None
                                                    else None)})
    return results, winner, potentials


def validate_winner(winner: dict, target: tuple[float, float] = TARGET) -> dict:
    """重复检查可观测、圆盘合法、时间及独立雅可比协方差迹。"""
    p, q = winner["station_a"], winner["station_b"]
    fleet = {v["id"]: (v["x"], v["y"]) for v in INITIAL_VEHICLE_POSITIONS}
    target_3d = (TARGETS[1]["x"], TARGETS[1]["y"], TARGETS[1]["z"])
    for vehicle, point, time in ((winner["vehicle_a"], p, winner["travel_time_a_s"]),
                                 (winner["vehicle_b"], q, winner["travel_time_b_s"])):
        if not straight_path_is_legal(fleet[vehicle], point):
            raise AssertionError("最优站位直线路径不是合法的车辆圆盘路径")
        if not math.isclose(math.dist(fleet[vehicle], point) / VEHICLE_SPEED, time, abs_tol=1e-9):
            raise AssertionError("行驶时间与经验证直线路径不一致")
        if not is_vehicle_position_valid(point, BUILDINGS, FIELD_SIZE, VEHICLE_RADIUS):
            raise AssertionError("最优站位车辆圆盘非法")
        if not check_observation_feasibility(point, target_3d)["feasible"]:
            raise AssertionError("最优站位不可观测")
        if not 0 <= time <= MAX_TRAVEL_TIME_S:
            raise AssertionError("行驶时间超限")
    metrics = calculate_localization_metrics(p, q, target)
    if p == q or metrics["degenerate"] or not math.isclose(metrics["rmse_m"], winner["rmse_m"], rel_tol=1e-12):
        raise AssertionError("精度复核不一致")
    jacobian = np.array([
        [-(target[1]-pt[1]) / math.dist(pt, target)**2,
         (target[0]-pt[0]) / math.dist(pt, target)**2]
        for pt in (p, q)
    ])
    covariance = math.radians(SIGMA_DEG)**2 * np.linalg.inv(jacobian) @ np.linalg.inv(jacobian).T
    independent_rmse = math.sqrt(float(np.trace(covariance)))
    if not math.isclose(independent_rmse, metrics["rmse_m"], rel_tol=1e-10):
        raise AssertionError("雅可比协方差复核不一致")
    return {"independent_jacobian_rmse_m": independent_rmse,
            "station_a_observable": True, "station_b_observable": True}


def save(results: list[dict], winner: dict, potentials: list[dict],
         verification: dict, directory: Path = INPUT_DIR) -> None:
    """仅新建文件，不覆盖 P1 或既有 P2 数据。"""
    with (directory / "p2_t2_pair_optima_v2.csv").open("x", newline="", encoding="utf-8") as stream:
        fields = ["vehicle_a", "vehicle_b", "station_a_x_m", "station_a_y_m",
                  "station_b_x_m", "station_b_y_m", "travel_time_a_s", "travel_time_b_s",
                  "baseline_m", "gamma_deg", "r1_m", "r2_m", "alpha1_deg", "alpha2_deg", "rmse_m"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = {k: result.get(k, "") for k in fields}
            if "station_a" in result:
                row.update(dict(zip(fields[2:6], (*result["station_a"], *result["station_b"]))))
            writer.writerow(row)
    with (directory / "p2_t2_pending_potential_v2.csv").open("x", newline="", encoding="utf-8") as stream:
        fields = ["vehicle_a", "vehicle_b", "geometric_better_pairs",
                  "promising_pending_a", "promising_pending_b", "best_relaxed_stations",
                  "best_relaxed_rmse_m"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(potentials)
    with (directory / "p2_t2_optimum_summary_v2.json").open("x", encoding="utf-8") as stream:
        json.dump({"scope": "confirmed-reachable 0.5m T2 grid; pending relaxation also checked",
                   "winner": winner, "verification": verification,
                   "pending_geometric_relaxation": potentials},
                  stream, ensure_ascii=False, indent=2, allow_nan=False)


def plot_solution(winner: dict, directory: Path = INPUT_DIR) -> None:
    """论文用双站交会图；同类车辆统一蓝色，线型区分分配。"""
    from matplotlib.patches import Rectangle
    from geometry_B.figure_style import COLORS, apply_figure_style, plt

    apply_figure_style()
    fleet = {v["id"]: (v["x"], v["y"]) for v in INITIAL_VEHICLE_POSITIONS}
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    for building in BUILDINGS:
        ax.add_patch(Rectangle((building["x_min"], building["y_min"]),
                               building["x_max"] - building["x_min"],
                               building["y_max"] - building["y_min"],
                               facecolor=COLORS["building"], edgecolor="none"))
    for key, vehicle, point, linestyle, marker in (
        ("a", winner["vehicle_a"], winner["station_a"], "-", "o"),
        ("b", winner["vehicle_b"], winner["station_b"], "--", "s"),
    ):
        start = fleet[vehicle]
        ax.plot((start[0], point[0]), (start[1], point[1]),
                color=COLORS["vehicle"], linestyle=linestyle, linewidth=2,
                label=f"V{vehicle} route")
        ax.plot((point[0], TARGET[0]), (point[1], TARGET[1]),
                color=COLORS["vehicle"], linestyle=":", linewidth=1.5,
                label="Bearing lines" if key == "a" else "_nolegend_")
        ax.scatter(*start, marker="x", s=65, color=COLORS["vehicle"], linewidth=1.8)
        ax.scatter(*point, marker=marker, s=55, facecolor="white",
                   edgecolor=COLORS["vehicle"], linewidth=1.7, zorder=4)
        offset = (5, -17) if key == "a" else (5, 9)
        ax.annotate(f"V{vehicle} station", point, xytext=offset,
                    textcoords="offset points", fontsize=9)
    ax.scatter(*TARGET, marker="*", s=125, color=COLORS["target"], zorder=5,
               label="T2 target")
    ax.annotate("T2", TARGET, xytext=(7, -1), textcoords="offset points", fontsize=9)
    ax.set(xlim=(0, FIELD_SIZE), ylim=(0, FIELD_SIZE),
           xlabel="x (m, east)", ylabel="y (m, north)",
           title=f"T2 intersection | RMSE {winner['rmse_m']:.4f} m")
    ax.set_aspect("equal")
    ax.legend(loc="lower right", frameon=True)
    with (directory / "p2_intersection_geometry.png").open("xb") as stream:
        fig.savefig(stream, format="png")
    plt.close(fig)


def main() -> tuple[list[dict], dict, list[dict]]:
    candidates = read_candidates()
    results, winner, potential = optimize(candidates)
    verification = validate_winner(winner)
    save(results, winner, potential, verification)
    plot_solution(winner)
    return results, winner, potential


if __name__ == "__main__":
    pair_results, best, pending = main()
    print("pairs:", [(r["vehicle_a"], r["vehicle_b"], round(r["rmse_m"], 8)) for r in pair_results])
    print("confirmed-grid winner:", best)
    print("pending potentials:", pending)
