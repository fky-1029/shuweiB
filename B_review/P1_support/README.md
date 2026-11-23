# P1 支撑材料

## 范围与来源

本目录是审查用快照，源代码复制自项目 `shared/` 与 `geometry_B/`，数值结果复制自 `figures/p1_t1_*`。代码未针对支撑包修改；此快照不是独立完整仓库，命令从原项目根目录运行。关键数据：`T1_0p5m.csv` 为 0.5 m 网格可观测点；`p1_t1_observable_grid_0p5m.npz` 是布尔网格；圆周扫描与部署 CSV/JSON 记录离散候选和计算结果。

## 文件

- `src/shared/constants.py`、`geometry_interface.py`：原题参数、车辆几何、有限视线遮挡、仰角和可观测性综合判定。
- `src/geometry_B/geometry_debug.py`、`observable_region_plot.py`、`figure_style.py`：网格判定和绘图依赖。
- `generate_region.py`、`generate_observable_points.py`：可观测网格生成入口；这些入口会写输出，不是只读复核命令。
- `p1_diagnostics.py`、`p1_optimal_station.py`、`p1_circle_analysis.py`：诊断、网格站位及理论仰角下界圆的分析。
- `data/`：相应 CSV/NPZ/JSON 原始结果副本。

## 复核结论（摘要）

T1 坐标为 `(84.6410161514,70,45) m`，摄像头高度 2 m；最大仰角 80° 给出 `r* = 43/tan(80°) = 7.58206017046 m` 和 `Q*=1/r*=0.1318903 m⁻¹`。已记录精确可行见证 `(80.0020731661,75.9973197687)` 达到距离下界；这是连续质量最优见证。网格 22,788/40,401=56.4% 是离散计数。论文表格的三位小数坐标 `(80.002,75.997)` 不能直接当严格可行坐标：实测仰角约 80.000269°，超出 80° 上限。应报告精确见证或解释舍入坐标仅作展示。

1° 圆周扫描记录 360 个角度样本、284 个修正后可行样本；这是离散候选集合。部署时间 5.064533 s 的 V4 样本属于该离散集合结论，不能据此声称连续圆周部署时间最优。代码 JSON 明确将 `continuous_circle_deployment_optimum_proven` 置为 false。

## 复现

在原项目根目录、已安装 `requirements.txt` 依赖的环境中：

```bash
.venv/bin/python -m unittest geometry_B.test_observation_constraints geometry_B.test_occlusion geometry_B.test_p1_circle_analysis -v
```

上述测试只读已有代码和内存，不应覆盖图表。需重新计算时可单独执行：

```bash
.venv/bin/python -m geometry_B.generate_observable_points
.venv/bin/python -m geometry_B.generate_region
.venv/bin/python -m geometry_B.p1_diagnostics
.venv/bin/python -m geometry_B.p1_circle_analysis
```

生成入口写项目中的共享数据或 `figures/`；重新运行前应检查目标文件行为，勿在原项目上盲目覆盖。

依赖：Python 3、NumPy、Matplotlib；pytest 仅在使用 pytest 时需要。该快照中测试文件与实现文件一起保存。
