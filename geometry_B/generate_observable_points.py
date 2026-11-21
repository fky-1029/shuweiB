"""生成供调度使用的 T1、T2、T3 全部 0.5 m 可观测网格点。

从项目根目录执行：.venv/bin/python -m geometry_B.generate_observable_points
只写入 shared/observable_points 下的 CSV，不进行候选点筛选或优化。
"""

from pathlib import Path

import numpy as np

from geometry_B.geometry_debug import make_observability_evaluator, sample_observability_grid
from shared.constants import TARGETS


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "shared" / "observable_points"


def generate_all(output_directory: Path = OUTPUT_DIRECTORY) -> dict[str, int]:
    """复用综合几何接口计算三个目标并保存全部合法点，返回各自点数。"""
    output_directory.mkdir(parents=True, exist_ok=True)
    counts = {}
    for target in TARGETS:
        target_id = f"T{target['id']}"
        x_values, y_values, observable = sample_observability_grid(
            make_observability_evaluator(target), spacing=0.5
        )
        rows, cols = np.nonzero(observable)
        points = np.column_stack((x_values[cols], y_values[rows]))
        np.savetxt(
            output_directory / f"{target_id}_0p5m.csv",
            points,
            delimiter=",",
            header="x_east_m,y_north_m",
            comments="",
            fmt="%.6f",
        )
        counts[target_id] = len(points)
    return counts


if __name__ == "__main__":
    for target_id, count in generate_all().items():
        print(f"{target_id}: {count} 个可观测网格点")
