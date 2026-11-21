"""P1 可观测区域绘图工具。

本模块只负责网格坐标生成、场景底图和已计算布尔结果的显示；
不实现、猜测或替代任何几何判定算法。调用方必须显式提供结果计算器。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from shared.constants import BUILDINGS, FIELD_SIZE, TARGETS


DEFAULT_GRID_SPACING = 0.5


def sample_field_grid(
    spacing: float = DEFAULT_GRID_SPACING,
    field_size: float = FIELD_SIZE,
) -> tuple[np.ndarray, np.ndarray]:
    """生成真实场地坐标网格，返回 ``(x_values, y_values)``。

    网格包含 0 和 ``field_size``；间距可调整，末端网格点不强行超过场地边界。
    """
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    if field_size <= 0:
        raise ValueError("field_size must be positive")

    count = int(np.floor(field_size / spacing + 1e-12))
    values = spacing * np.arange(count + 1, dtype=float)
    if not np.isclose(values[-1], field_size):
        values = np.append(values, float(field_size))
    else:
        values[-1] = float(field_size)
    return values, values.copy()


def evaluate_grid(
    evaluator: Callable[[tuple[float, float]], bool],
    x_values: Sequence[float],
    y_values: Sequence[float],
) -> np.ndarray:
    """将调用方已经确定的可观测性判定应用到网格。

    ``evaluator`` 的异常会原样传播；因此未实现的判定不会被伪装成 False。
    返回数组形状为 ``(len(y_values), len(x_values))``，适用于 ``pcolormesh``。
    """
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    result = np.empty((len(y_values), len(x_values)), dtype=bool)
    for j, y in enumerate(y_values):
        for i, x in enumerate(x_values):
            result[j, i] = bool(evaluator((float(x), float(y))))
    return result


def plot_field(
    *,
    observable: Optional[np.ndarray] = None,
    x_values: Optional[Sequence[float]] = None,
    y_values: Optional[Sequence[float]] = None,
    buildings: Sequence[dict] = BUILDINGS,
    target: dict = TARGETS[0],
    ax: Optional[Axes] = None,
) -> tuple[Figure, Axes]:
    """绘制场地、建筑投影和 T1；可选地叠加已验证的布尔网格。

    不传 ``observable`` 时只绘制场景底图。传入结果时必须同时传入坐标轴，
    且数组形状必须为 ``(len(y_values), len(x_values))``。
    """
    if (observable is None) != (x_values is None or y_values is None):
        raise ValueError("observable requires both x_values and y_values")
    if observable is not None:
        expected_shape = (len(y_values), len(x_values))
        if np.asarray(observable).shape != expected_shape:
            raise ValueError(f"observable shape must be {expected_shape}")

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    else:
        fig = ax.figure

    if observable is not None:
        # 只显示 True 区域；False 区域保持白底，避免暗示“已计算为不可观测”。
        mask = np.ma.masked_where(~np.asarray(observable, dtype=bool), observable)
        ax.pcolormesh(
            np.asarray(x_values), np.asarray(y_values), mask,
            shading="auto", cmap="Greens", alpha=0.35,
        )

    for building in buildings:
        ax.add_patch(Rectangle(
            (building["x_min"], building["y_min"]),
            building["x_max"] - building["x_min"],
            building["y_max"] - building["y_min"],
            facecolor="#9aa3ad", edgecolor="#4b5563", linewidth=1.0,
        ))
        ax.text(
            (building["x_min"] + building["x_max"]) / 2,
            (building["y_min"] + building["y_max"]) / 2,
            f"B{building['id']}", ha="center", va="center", color="#17202a",
        )

    ax.scatter(target["x"], target["y"], marker="^", s=75, c="#c2410c",
               edgecolors="white", linewidths=0.8, zorder=4, label="T1")
    ax.set_xlim(0, FIELD_SIZE)
    ax.set_ylim(0, FIELD_SIZE)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("East x / m")
    ax.set_ylabel("North y / m")
    ax.set_title(
        "P1: T1 observable region (sampled grid)"
        if observable is not None else "P1: field and T1 (observability not evaluated)"
    )
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper right")
    return fig, ax


def save_scene(path: str | Path, **plot_kwargs) -> None:
    """保存底图或调用方提供的结果图；不会自行计算可观测区域。"""
    fig, _ = plot_field(**plot_kwargs)
    fig.savefig(path, dpi=160)
    plt.close(fig)
