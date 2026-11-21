"""P1 T1 客观指标与边界抽样核验；不搜索或选取站位。

从项目根目录：.venv/bin/python -m geometry_B.p1_diagnostics
直接使用已保存的 0.5 m 网格和 CSV；不重新生成或覆盖它们。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from geometry_B.observable_region_plot import plot_field
from shared.constants import FIELD_SIZE, GIMBAL_PITCH_MAX, GIMBAL_PITCH_MIN, TARGETS, get_observable_points
from shared.geometry_interface import (
    calculate_elevation_angle, calculate_horizontal_distance,
    check_observation_feasibility,
)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
SOURCE_CSV = ROOT / "shared" / "observable_points" / "T1_0p5m.csv"
SOURCE_NPZ = FIGURES / "p1_t1_observable_grid_0p5m.npz"
SEED = 20261121


def _boundary_cells(mask: np.ndarray) -> np.ndarray:
    """网格内四邻点类别有变化的格点；非连续几何边界。"""
    boundary = np.zeros_like(mask, dtype=bool)
    change_y = mask[1:] != mask[:-1]
    change_x = mask[:, 1:] != mask[:, :-1]
    boundary[1:] |= change_y
    boundary[:-1] |= change_y
    boundary[:, 1:] |= change_x
    boundary[:, :-1] |= change_x
    return np.argwhere(boundary)


def _save_hist(data, xlabel, title, filename):
    fig, ax = plt.subplots(figsize=(8, 5.5), layout="constrained")
    ax.hist(data, bins=55, color="#338CC9", edgecolor="white", linewidth=0.35)
    ax.set(xlabel=xlabel, ylabel="Sampled feasible grid points (count)", title=title)
    ax.grid(axis="y", alpha=0.18)
    fig.savefig(FIGURES / filename, dpi=300)
    fig.savefig(FIGURES / filename.replace(".png", ".svg"))
    plt.close(fig)


def run() -> dict:
    with SOURCE_CSV.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["x_east_m", "y_north_m"]:
            raise ValueError("T1 CSV 坐标列不符")
        points = np.asarray([(float(row["x_east_m"]), float(row["y_north_m"])) for row in reader])
    with np.load(SOURCE_NPZ) as data:
        x, y, mask = data["x_values"], data["y_values"], data["observable"]
    if mask.shape != (201, 201) or mask.dtype != np.bool_:
        raise ValueError("已有 NPZ 网格不是 201×201 布尔矩阵")
    if not (np.allclose(np.diff(x), 0.5) and np.allclose(np.diff(y), 0.5)
            and x[0] == y[0] == 0 and x[-1] == y[-1] == FIELD_SIZE):
        raise ValueError("现有网格坐标或间距不符合 0.5 m")
    j, i = np.nonzero(mask)
    expected = np.column_stack((x[i], y[j]))
    if points.shape != expected.shape or not np.array_equal(points, expected):
        raise ValueError("CSV 与已有网格不一致（含顺序/重复/缺失核对）")
    if not np.isfinite(points).all() or len(np.unique(points, axis=0)) != len(points):
        raise ValueError("T1 CSV 存在非有限数或重复点")
    if np.any((points < 0) | (points > FIELD_SIZE)) or not np.array_equal(
            points, np.asarray(get_observable_points("T1"))):
        raise ValueError("读取接口、坐标范围或 CSV 不一致")

    target = TARGETS[0]
    target_position = (target["x"], target["y"], target["z"])
    if not np.allclose(target_position, (84.64, 70.00, 45.00), atol=0.005):
        raise ValueError("T1 与题面两位小数坐标不符")
    r = np.fromiter((calculate_horizontal_distance(tuple(p), target_position) for p in points), float)
    theta = np.fromiter((calculate_elevation_angle(tuple(p), target_position) for p in points), float)
    if not np.isfinite(r).all() or (r <= 0).any():
        raise ValueError("水平距离有非有限值或零值，Q=1/r 不适用")
    quality = 1 / r  # 仅为用户指定的水平距离倒数，不是双站定位精度。
    if not np.isfinite(theta).all() or not np.isfinite(quality).all() or (quality <= 0).any():
        raise ValueError("仰角或质量指标非有限或不合理")
    if np.any((theta < GIMBAL_PITCH_MIN - 1e-8) | (theta > GIMBAL_PITCH_MAX + 1e-8)):
        raise ValueError("已有合法点的仰角不在云台范围")
    # 完整合法点再判定一次，核对现有 CSV 与当前综合接口的一致性。
    if any(not check_observation_feasibility(tuple(p), target_position)["feasible"] for p in points):
        raise ValueError("有 CSV 合法点未通过当前综合接口")
    table = FIGURES / "p1_t1_observable_metrics_0p5m.csv"
    with table.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("x_east_m", "y_north_m", "r_horizontal_m", "theta_elevation_deg", "Q_inverse_m"))
        writer.writerows((f"{p[0]:.6f}", f"{p[1]:.6f}", f"{ri:.12g}", f"{ti:.12g}", f"{qi:.12g}")
                         for p, ri, ti, qi in zip(points, r, theta, quality))

    # 在离散类别变化的网格边附近抽取可复现样本，在网格点和其周围
    # 小幅偏移处调用连续判定；偏移点不按网格标签强行假定结果。
    cells = _boundary_cells(mask)
    rng = np.random.default_rng(SEED)
    sample = cells[rng.choice(len(cells), size=min(60, len(cells)), replace=False)]
    checks = FIGURES / "p1_t1_boundary_checks_0p5m.csv"
    mismatch = 0
    with checks.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("grid_x_m", "grid_y_m", "mask_feasible", "direct_feasible", "offset_x_m", "offset_y_m", "offset_feasible"))
        for row, col in sample:
            px, py = float(x[col]), float(y[row])
            direct = check_observation_feasibility((px, py), target_position)["feasible"]
            mismatch += direct != bool(mask[row, col])
            # 固定偏移，均落在场地内；不将离散边界误称连续边界。
            ox, oy = float(np.clip(px + 0.125, 0, FIELD_SIZE)), float(np.clip(py + 0.125, 0, FIELD_SIZE))
            offset = check_observation_feasibility((ox, oy), target_position)["feasible"]
            writer.writerow((px, py, int(mask[row, col]), int(direct), ox, oy, int(offset)))
    if mismatch:
        raise ValueError(f"离散边界格点与直接判定不一致：{mismatch}")

    def stats(arr):
        return {"min": float(np.min(arr)), "p05": float(np.percentile(arr, 5)),
                "median": float(np.median(arr)), "mean": float(np.mean(arr)),
                "p95": float(np.percentile(arr, 95)), "max": float(np.max(arr))}

    summary = {"source_csv": str(SOURCE_CSV.relative_to(ROOT)),
               "source_npz": str(SOURCE_NPZ.relative_to(ROOT)),
               "target_xyz_m": list(target_position), "grid_spacing_m": 0.5,
               "grid_shape_yx": list(mask.shape), "valid_points": len(points),
               "invalid_grid_points": int((~mask).sum()), "unique_points": len(np.unique(points, axis=0)),
               "boundary_grid_cells": len(cells), "boundary_sample_count": len(sample),
               "boundary_grid_mismatch_count": mismatch, "boundary_offset_m": [0.125, 0.125],
               "sample_seed": SEED, "r_horizontal_m": stats(r),
               "theta_elevation_deg": stats(theta), "Q_inverse_m": stats(quality),
               "nan_or_inf_count": 0,
               "note": "只有网格边缘样本与偏移点直接判定；并非连续边界证明或最优站位。"}
    (FIGURES / "p1_t1_diagnostics_0p5m.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _save_hist(r, "Horizontal distance r / m", "T1: distance distribution (feasible grid)",
               "p1_t1_distance_distribution_0p5m.png")
    _save_hist(theta, "Elevation angle θ / degrees", "T1: elevation distribution (feasible grid)",
               "p1_t1_elevation_distribution_0p5m.png")
    fig, ax = plot_field(observable=mask, x_values=x, y_values=y)
    fig.savefig(FIGURES / "p1_t1_observable_region_0p5m.svg", dpi=300,
                bbox_inches="tight")
    plt.close(fig)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
