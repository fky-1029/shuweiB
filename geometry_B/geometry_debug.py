"""几何接口与可视化连接的运行/调试入口，不计算或伪造区域结果。"""

from __future__ import annotations

from collections.abc import Callable

from shared.constants import BUILDINGS, TARGETS
from shared.geometry_interface import check_observation_feasibility
from geometry_B.observable_region_plot import evaluate_grid, sample_field_grid


def make_observability_evaluator(
    target: dict = TARGETS[0],
    buildings: list[dict] = BUILDINGS,
) -> Callable[[tuple[float, float]], bool]:
    """将综合接口适配为绘图网格所需的 ``position -> bool`` 调用形式。

    综合接口未实现时会保留 ``NotImplementedError``，不会把失败当作不可观测。
    """
    target_position = (target["x"], target["y"], target["z"])

    def evaluator(vehicle_position: tuple[float, float]) -> bool:
        result = check_observation_feasibility(
            vehicle_position, target_position, buildings
        )
        return bool(result["feasible"])

    return evaluator


def sample_observability_grid(
    evaluator: Callable[[tuple[float, float]], bool],
    spacing: float = 0.5,
):
    """运行实际 evaluator 并返回 ``(x_values, y_values, mask)``。

    该函数是后续实现完成后的调试入口；当前调用未实现接口会明确失败。
    """
    x_values, y_values = sample_field_grid(spacing=spacing)
    mask = evaluate_grid(evaluator, x_values, y_values)
    return x_values, y_values, mask
