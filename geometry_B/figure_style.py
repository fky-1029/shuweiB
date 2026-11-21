"""论文 P1 图统一样式，遵照 main/shared/figure_style_guide.md（2026-11-21）。"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = {
    "building": "#7f7f7f",
    "vehicle": "#1f77b4",
    "target": "#d62728",
    "feasible": "#2ca02c",
    "infeasible": "#ff9896",
}


def apply_figure_style() -> None:
    """设置 matplotlib 出图参数；仅影响调用进程的绘图，不影响几何数据。"""
    plt.rcParams.update({
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.axisbelow": True,
    })
