"""用真实几何接口生成 T1 的网格可观测区域及可复核数据。

运行：从项目根目录执行 .venv/bin/python -m geometry_B.generate_region
"""

from pathlib import Path

import numpy as np

from geometry_B.geometry_debug import make_observability_evaluator, sample_observability_grid
from geometry_B.observable_region_plot import DEFAULT_GRID_SPACING, save_scene
from shared.constants import FIELD_SIZE, TARGETS


def generate(output_directory: str | Path = "figures", spacing: float = DEFAULT_GRID_SPACING) -> tuple[int, int]:
    """计算并保存网格结果；返回（有效点数，网格总点数）。"""
    target = TARGETS[0]
    evaluator = make_observability_evaluator(target)
    x_values, y_values, observable = sample_observability_grid(evaluator, spacing)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    # mask[j, i] 对应 (x_values[i], y_values[j])，行是北向 y、列是东向 x。
    np.savez_compressed(
        output_directory / "p1_t1_observable_grid_0p5m.npz",
        x_values=x_values,
        y_values=y_values,
        observable=observable,
        spacing=np.array(spacing),
        field_size=np.array(FIELD_SIZE),
        target_xyz=np.array([target["x"], target["y"], target["z"]]),
    )
    rows, cols = np.nonzero(observable)
    valid_points = np.column_stack((x_values[cols], y_values[rows]))
    np.savetxt(
        output_directory / "p1_t1_observable_points_0p5m.csv",
        valid_points,
        delimiter=",",
        header="x_east_m,y_north_m",
        comments="",
        fmt="%.6f",
    )
    save_scene(
        output_directory / "p1_t1_observable_region_0p5m.png",
        observable=observable, x_values=x_values, y_values=y_values, target=target,
    )
    return len(valid_points), observable.size


if __name__ == "__main__":
    valid, total = generate()
    print(f"T1 可观测网格点：{valid} / {total}")
