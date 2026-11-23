"""P1 T1 0.5 m 网格候选的可复核计算与连续点验证入口。

该模块不实施连续最优搜索；复用 p1_diagnostics 对 CSV、NPZ、公共几何接口
和全体网格指标做完整核验。运行：.venv/bin/python -m geometry_B.p1_optimal_station
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from geometry_B.p1_diagnostics import run as run_grid_diagnostics
from shared.constants import TARGETS
from shared.geometry_interface import (
    calculate_elevation_angle,
    calculate_horizontal_distance,
    check_observation_feasibility,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "figures" / "p1_t1_diagnostics_0p5m.json"
GRID_CANDIDATE = (80.0, 76.0)
EXPECTED_R_M = 7.58544862993
EXPECTED_THETA_DEG = 79.9956212159
EXPECTED_Q_PER_M = 0.131831358801


def evaluate_station(position: tuple[float, float], target_id: str = "T1") -> dict:
    """使用共享几何接口复核一个明确给出的点，不作站位优化。"""
    target = next((item for item in TARGETS if f"T{item['id']}" == target_id), None)
    if target is None:
        raise ValueError("target_id 必须是 T1、T2 或 T3")
    if len(position) != 2 or not all(math.isfinite(value) for value in position):
        raise ValueError("position 必须是有限的二维坐标")
    target_xyz = (target["x"], target["y"], target["z"])
    feasibility = check_observation_feasibility(position, target_xyz)
    r = calculate_horizontal_distance(position, target_xyz)
    theta = calculate_elevation_angle(position, target_xyz)
    return {
        "position_xy_m": [float(position[0]), float(position[1])],
        "target_xyz_m": list(target_xyz),
        "feasible": bool(feasibility["feasible"]),
        "feasibility_reason": feasibility.get("reason", ""),
        "r_horizontal_m": float(r),
        "theta_elevation_deg": float(theta),
        "Q_inverse_m": float(1.0 / r) if r > 0 else None,
    }


def verify_grid_candidate() -> dict:
    """核验当前已知网格候选，并确认其来自既有全量网格指标表。"""
    # 每次重新核验现有原始网格/CSV 并据此刷新指标表，避免读取过期的缓存文件。
    run_grid_diagnostics()
    result = evaluate_station(GRID_CANDIDATE)
    expected = (EXPECTED_R_M, EXPECTED_THETA_DEG, EXPECTED_Q_PER_M)
    observed = (result["r_horizontal_m"], result["theta_elevation_deg"], result["Q_inverse_m"])
    if not result["feasible"]:
        raise AssertionError("指定网格候选未通过共享可行性判定")
    if not np.allclose(observed, expected, rtol=0, atol=5e-10):
        raise AssertionError(f"网格候选数值不一致：{observed}")
    import csv
    metrics = ROOT / "figures" / "p1_t1_observable_metrics_0p5m.csv"
    minimum_r = math.inf
    minimizers = []
    count = 0
    match = None
    with metrics.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        for row in rows:
            count += 1
            location = (float(row["x_east_m"]), float(row["y_north_m"]))
            row_r = float(row["r_horizontal_m"])
            if not math.isfinite(row_r) or row_r <= 0:
                raise AssertionError("网格指标表包含无效距离")
            if row_r < minimum_r:
                minimum_r = row_r
                minimizers = [location]
            elif row_r == minimum_r:
                minimizers.append(location)
            if location == GRID_CANDIDATE:
                match = row
    if count != 22788 or minimizers != [GRID_CANDIDATE]:
        raise AssertionError(f"网格最小距离核对失败：行数 {count}，最小点 {minimizers}")
    if match is None:
        raise AssertionError("(80,76) 不在现有 T1 可观测网格指标表中")
    table_values = tuple(float(match[key]) for key in
                          ("r_horizontal_m", "theta_elevation_deg", "Q_inverse_m"))
    if not np.allclose(table_values, expected, rtol=0, atol=5e-10):
        raise AssertionError(f"指标表中的候选数值不一致：{table_values}")
    result["status"] = "已验证的 0.5 m 网格最优候选；不是连续全局最优结论"
    result["grid_metric_row"] = match
    return result


def validate_continuous_candidate(position: tuple[float, float], target_id: str = "T1") -> dict:
    """连续坐标候选验证入口：只判可行性并报告指标，不作全局性声明。"""
    result = evaluate_station(position, target_id=target_id)
    result["status"] = "单点连续坐标可行性已判定；未证明局部或全局最优"
    return result


def run() -> dict:
    candidate = verify_grid_candidate()
    summary = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    result = {
        "grid_audit": summary,
        "grid_optimal_candidate": candidate,
        "continuous_global_optimum_established": False,
        "theoretical_horizontal_distance_lower_bound_m": 43.0 / math.tan(math.radians(80.0)),
        "theoretical_bound_note": (
            "若目标与摄像头高度差固定为 43 m，且仰角 theta<=80°，则 r>=43/tan(80°)。"
            "该下界由仰角约束推出；尚未验证其能否同时满足场地、车辆避碰和遮挡约束，不能视为可达最优值。"
        ),
    }
    (ROOT / "figures" / "p1_t1_grid_candidate_0p5m.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
