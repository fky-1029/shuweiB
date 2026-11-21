# 论文图规范（统一版）

> 2026-11-21 定稿。所有进入论文的图按此规范生成，C 负责收口。
> 原则：同一对象在所有图中用同一颜色，命名统一，风格一致。

## 1. 命名

统一 `p{问题号}_{内容}.png`，小写英文 + 下划线。

| 图 | 文件名 |
|---|---|
| 场地图 | field_layout.png |
| P1 可观测区域 | p1_observable_region.png |
| P2(1) 交会几何 | p2_intersection_geometry.png |
| P2(1) 精度图 | p2_accuracy.png |
| P2(2) 路径图 | p2_routing.png |
| P2(2) 时间线 | p2_timeline.png |
| P3 误差图 | p3_error.png |
| P4 重调度对比 | p4_rescheduling.png |

## 2. 格式与分辨率

- PNG，dpi ≥ 200
- 单图 `figsize≈(6, 4.5)`；并排双图每个 `(4.5, 4)`

## 3. 统一配色（同一对象永远同一颜色）

| 对象 | 颜色 | 色值 |
|---|---|---|
| 建筑 | 灰 | `#7f7f7f` |
| 车辆 | 蓝 | `#1f77b4` |
| 目标 | 红 | `#d62728` |
| 可观测/可行 | 绿 | `#2ca02c` |
| 不可观测 | 浅红 | `#ff9896` |

## 4. 字体字号

轴标签 12 · 标题 13 · 刻度/图例 10

## 5. 坐标轴与图例

- 轴必须带单位和方向：`x (m, east)`、`y (m, north)`、`time (s)`
- 网格开（`alpha=0.3`，放数据下方）
- 图例放不挡数据的位置
- 场地类图必须 `axis equal`（x/y 等比例）

## 6. 出图脚本统一头部

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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

COLORS = {
    "building":   "#7f7f7f",
    "vehicle":    "#1f77b4",
    "target":     "#d62728",
    "feasible":   "#2ca02c",
    "infeasible": "#ff9896",
}
```
