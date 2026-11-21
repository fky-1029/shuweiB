"""P2(1) 退化分析、仰角边界实验及离散几何松弛审计。

只读取已生成的 T2 可观测站位、可达性表及名义最优表；
不重复原始 80° 全量优化，不规划绕障路径。
运行：.venv/bin/python -m geometry_B.p2_final_analysis
"""
from __future__ import annotations

import csv
from itertools import combinations
import math
from pathlib import Path

import numpy as np

from geometry_B.p2_localization_accuracy import calculate_localization_metrics
from geometry_B.p2_two_station_optimize import (
    INPUT_DIR, TARGET, read_candidates, search_pair, validate_winner,
)
from shared.constants import CAMERA_HEIGHT, TARGETS
from shared.geometry_interface import check_observation_feasibility

CAPS_DEG = (80.0, 79.5, 79.0)
SIGMA_RAD = math.radians(1)
# Only guards the scalar audit's floating-point pruning boundary; not a geometry cutoff.
PRUNE_MARGIN = 1e-12


def elevation_deg(point: tuple[float, float]) -> float:
    """Camera-to-target elevation, using shared camera height and T2 altitude."""
    return math.degrees(math.atan2(TARGETS[1]["z"] - CAMERA_HEIGHT,
                                   math.dist(point, TARGET)))


def filter_elevation(candidates: dict, cap_deg: float) -> dict:
    if not 0 < cap_deg < 90:
        raise ValueError("仰角上限必须处于 (0°, 90°)")
    return {
        vehicle: {status: {point: value for point, value in groups[status].items()
                           if elevation_deg(point) <= cap_deg}
                  for status in ("confirmed", "pending")}
        for vehicle, groups in candidates.items()
    }


def read_nominal_pairs(directory: Path = INPUT_DIR) -> list[dict]:
    with (directory / "p2_t2_pair_optima_v2.csv").open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    if len(records) != 10 or {(int(r["vehicle_a"]), int(r["vehicle_b"])) for r in records} != set(combinations(range(1, 6), 2)):
        raise ValueError("名义最优表必须完整包含 10 个车辆组合")
    result = []
    for r in records:
        a, b = int(r["vehicle_a"]), int(r["vehicle_b"])
        p = (float(r["station_a_x_m"]), float(r["station_a_y_m"]))
        q = (float(r["station_b_x_m"]), float(r["station_b_y_m"]))
        result.append({"vehicle_a": a, "vehicle_b": b, "station_a": p,
                       "station_b": q, "rmse_m": float(r["rmse_m"]),
                       "travel_time_a_s": float(r["travel_time_a_s"]),
                       "travel_time_b_s": float(r["travel_time_b_s"])})
    return result


def cap_experiment(candidates: dict, nominal: list[dict], cap_deg: float) -> dict:
    """重新筛站位及其直达证明，只在较严格的新集合上重新精确搜索。"""
    filtered = filter_elevation(candidates, cap_deg)
    if cap_deg == 80.0:
        results = nominal  # User requested no rerun of existing full-size search.
    else:
        results = []
        for a, b in combinations(sorted(filtered), 2):
            answer = search_pair(filtered[a]["confirmed"], filtered[b]["confirmed"], TARGET)
            if answer["stations"] is not None:
                p, q = answer["stations"]
                results.append({"vehicle_a": a, "vehicle_b": b,
                                "station_a": p, "station_b": q,
                                "rmse_m": calculate_localization_metrics(p, q, TARGET)["rmse_m"],
                                "travel_time_a_s": filtered[a]["confirmed"][p],
                                "travel_time_b_s": filtered[b]["confirmed"][q]})
    winner = min(results, key=lambda row: row["rmse_m"])
    ties = [r for r in results if math.isclose(r["rmse_m"], winner["rmse_m"], abs_tol=1e-12)]
    for row in ties:
        for vehicle, key in ((row["vehicle_a"], "station_a"), (row["vehicle_b"], "station_b")):
            if row[key] not in filtered[vehicle]["confirmed"]:
                raise AssertionError("优选站位未获得直达行驶证明")
            observation = check_observation_feasibility(
                row[key], (TARGETS[1]["x"], TARGETS[1]["y"], TARGETS[1]["z"])
            )
            if not observation["feasible"] or observation["elevation_angle"] > cap_deg:
                raise AssertionError("优选站位未满足完整可观测约束及新仰角上限")
            if filtered[vehicle]["confirmed"][row[key]] > 30:
                raise AssertionError("优选站位行驶超时")
    metrics = calculate_localization_metrics(winner["station_a"], winner["station_b"], TARGET)
    if not math.isclose(metrics["rmse_m"], winner["rmse_m"], abs_tol=1e-12):
        raise AssertionError("新解 RMSE 与原精度模块不一致")
    # Existing independent Jacobian and continuous-path checker validates 80° nominal
    # and can also validate new optima, since tighter caps imply original feasibility.
    verification = validate_winner(winner)
    return {"cap_deg": cap_deg, "min_horizontal_range_m":
            (TARGETS[1]["z"] - CAMERA_HEIGHT) / math.tan(math.radians(cap_deg)),
            "confirmed_counts": {k: len(v["confirmed"]) for k, v in filtered.items()},
            "pending_counts": {k: len(v["pending"]) for k, v in filtered.items()},
            "pair_count": len(results), "winner": winner,
            "ties": ties, "metrics": metrics, "verification": verification}


def audit_pending(candidates: dict, threshold: float) -> dict:
    """独立标量审计下界未排除的所有含待验证站位的组合。

    逐点筛 r<=threshold/sigma 后，按 sigma*hypot(r1,r2) 剪枝；
    剩余用既有标量精度函数检查。既不查路径也不重跑主优化。
    """
    radius_cap = (threshold / SIGMA_RAD) * (1 + PRUNE_MARGIN)
    near = {
        k: [(p, status, math.dist(p, TARGET))
            for status in ("confirmed", "pending") for p in groups[status]
            if math.dist(p, TARGET) <= radius_cap]
        for k, groups in candidates.items()
    }
    total = sum((len(candidates[a]["confirmed"]) + len(candidates[a]["pending"])) *
                (len(candidates[b]["confirmed"]) + len(candidates[b]["pending"]))
                for a, b in combinations(candidates, 2))
    surviving = 0
    pending_surviving = 0
    improving = []
    best_pending = (math.inf, None)
    for a, b in combinations(candidates, 2):
        for p, sa, r1 in near[a]:
            for q, sb, r2 in near[b]:
                if SIGMA_RAD * math.hypot(r1, r2) > threshold * (1 + PRUNE_MARGIN):
                    continue
                surviving += 1
                if sa == sb == "confirmed":
                    continue
                pending_surviving += 1
                metric = calculate_localization_metrics(p, q, TARGET)
                if metric["rmse_m"] < threshold:
                    improving.append((a, b, p, q, metric["rmse_m"]))
                if metric["rmse_m"] < best_pending[0]:
                    best_pending = (metric["rmse_m"], (a, b, p, q, sa, sb))
    return {"total_screened_pair_combinations": total,
            "single_station_radius_kept_counts": {k: len(v) for k, v in near.items()},
            "pair_bound_survivors": surviving,
            "pending_pair_bound_survivors": pending_surviving,
            "pending_strict_improvers": improving,
            "best_pending_pair": best_pending}


def degeneration_series(r1: float, r2: float, angles_deg: tuple[float, ...]) -> list[dict]:
    """固定目标距的理论角度敏感性，不作为可行站位优化。"""
    factor = SIGMA_RAD * math.hypot(r1, r2)
    return [{"gamma_deg": angle,
             "rmse_m": (math.inf if abs(math.sin(math.radians(angle))) <= 1e-12
                        else factor / abs(math.sin(math.radians(angle))))}
            for angle in angles_deg]


def render_degeneracy_plot(r1: float, r2: float, output: Path) -> None:
    from geometry_B.figure_style import COLORS, apply_figure_style, plt

    apply_figure_style()
    angles = np.linspace(0.01, 179.99, 1200)
    values = SIGMA_RAD * math.hypot(r1, r2) / np.abs(np.sin(np.deg2rad(angles)))
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    ax.plot(angles, values, color=COLORS["vehicle"], linewidth=2,
            label="Fixed target ranges")
    for angle in (1, 5, 90, 175, 179):
        rmse = SIGMA_RAD * math.hypot(r1, r2) / abs(math.sin(math.radians(angle)))
        ax.scatter(angle, rmse, color=COLORS["feasible"], s=30, zorder=3)
    ax.axvline(90, color=COLORS["building"], linewidth=1, linestyle="--")
    ax.set(xlim=(0, 180), ylim=(0.1, 100), yscale="log",
           xlabel="Intersection angle (deg)",
           ylabel="Horizontal RMSE (m, log scale)",
           title="Bearing intersection sensitivity")
    ax.legend(loc="upper center", frameon=False)
    ax.text(.5, .9, "0° / 180°: degenerate; 1° / 179°: 8.27 m",
            ha="center", va="center", transform=ax.transAxes, fontsize=9,
            bbox=dict(facecolor="white", edgecolor="none", alpha=.85))
    ax.annotate("90°: 0.144 m", (90, SIGMA_RAD * math.hypot(r1, r2)),
                xytext=(7, 10), textcoords="offset points", fontsize=9)
    with output.open("xb") as stream:
        fig.savefig(stream, format="png")
    plt.close(fig)


def export_results(rows: list[dict], audit: dict, path: Path) -> None:
    """One compact paper-oriented comparison CSV; no redundant candidate exports."""
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("pitch_cap_deg", "min_horizontal_range_m", "vehicle_a", "vehicle_b",
                         "station_a_x_m", "station_a_y_m", "station_b_x_m", "station_b_y_m",
                         "time_a_s", "time_b_s", "r1_m", "r2_m", "baseline_m",
                         "alpha1_deg", "alpha2_deg", "gamma_deg", "rmse_m", "tied_vehicle_pairs",
                         *(f"v{k}_confirmed_count" for k in range(1, 6)),
                         *(f"v{k}_pending_count" for k in range(1, 6))))
        for row in rows:
            win, metrics = row["winner"], row["metrics"]
            writer.writerow((row["cap_deg"], row["min_horizontal_range_m"],
                             win["vehicle_a"], win["vehicle_b"], *win["station_a"],
                             *win["station_b"], win["travel_time_a_s"], win["travel_time_b_s"],
                             metrics["r1_m"], metrics["r2_m"], metrics["baseline_m"],
                             metrics["alpha1_deg"], metrics["alpha2_deg"],
                             metrics["gamma_deg"], metrics["rmse_m"],
                             ";".join(f"V{w['vehicle_a']}-V{w['vehicle_b']}" for w in row["ties"]),
                             *(row["confirmed_counts"][k] for k in range(1, 6)),
                             *(row["pending_counts"][k] for k in range(1, 6))))


def main() -> tuple[list[dict], dict]:
    candidates = read_candidates()
    nominal = read_nominal_pairs()
    rows = [cap_experiment(candidates, nominal, cap) for cap in CAPS_DEG]
    audits = {row["cap_deg"]: audit_pending(filter_elevation(candidates, row["cap_deg"]),
                                           row["winner"]["rmse_m"]) for row in rows}
    if any(audit["pending_strict_improvers"] for audit in audits.values()):
        raise AssertionError("待验证站位审计发现能够严格改进的网格点对")
    export_results(rows, audits[80.0], INPUT_DIR / "p2_t2_pitch_sensitivity.csv")
    render_degeneracy_plot(rows[0]["metrics"]["r1_m"], rows[0]["metrics"]["r2_m"],
                           INPUT_DIR / "p2_accuracy.png")
    return rows, audits


if __name__ == "__main__":
    results, check = main()
    for r in results:
        w = r["winner"]
        print(r["cap_deg"], r["confirmed_counts"],
              (w["vehicle_a"], w["vehicle_b"], w["station_a"], w["station_b"]),
              w["rmse_m"], [(p["vehicle_a"], p["vehicle_b"]) for p in r["ties"]])
    print("independent pending audits:", check)
