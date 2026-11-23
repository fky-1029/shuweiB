# P2(1) 支撑材料

## 范围与来源

此审查快照的源代码复制自 `shared/`、`geometry_B/`，数据复制自 `shared/observable_points/T2_0p5m.csv` 和 `figures/p2_t2_*`。目录保留模块包结构以供 Python import。结果快照不是运行时哈希清单；审查报告区分既有 CSV、程序复核与完整重跑。

## 文件及依赖

- `src/shared/constants.py`、`geometry_interface.py`：目标、障碍和几何可行性。
- `src/geometry_B/p2_localization_accuracy.py`：双站一阶 RMSE/几何量。
- `p2_two_station_tools.py`、`p2_vehicle_reachability.py`：几何辅助与直线路径可达性判定。
- `p2_two_station_optimize.py`：读取五车可达性输入，对可证直达的网格站位对搜索。
- `p2_final_analysis.py`：仰角敏感性和 pending 几何松弛分析。
- `data/` 保存 T2 网格、五车候选输入 CSV、v2 汇总、配对最优、pending 审计、仰角敏感性等结果。

## 模型与已知边界

观测角标准差为 1°，公式内转换为弧度。独立同方差 bearing 误差下，局部雅可比行是 `[-(y_T-y_i)/r_i², (x_T-x_i)/r_i²]`；非退化且小误差线性化时：

`RMSE = σ_rad sqrt(r1²+r2²)/|sin γ|`。

代码在有限精度阈值内将共线几何判为退化。T2 0.5 m 网格 26,037 点。名义离散结果：V1+V3，站位 `(8,67.5)`、`(6,75.5)` m，基线 8.246211 m、交会角 89.612206°，一阶水平 RMSE 0.144416384 m。仅为网格和一阶模型结论，不代表连续空间全局最优或非线性误差仿真。搜索使用已证直达候选；pending 绕行点对通过额外松弛审计，但逐车组合输出不应一律解释为包含全部绕障站位的逐对全局最优。

## 只读复核命令

从原项目根目录运行：

```bash
.venv/bin/python -m unittest geometry_B.test_p2_localization_accuracy geometry_B.test_p2_two_station_tools geometry_B.test_p2_vehicle_reachability geometry_B.test_p2_two_station_optimize geometry_B.test_p2_final_analysis -v
```

这组测试为只读计算；测试依赖 NumPy 和 pytest。完整优化入口会写输出且现有实现对已存在目标采用独占创建，勿在原项目目录盲目重复：

```bash
.venv/bin/python -m geometry_B.p2_two_station_optimize
.venv/bin/python -m geometry_B.p2_final_analysis
```

依赖：Python 3、NumPy；图表导出另需 Matplotlib。搜索和敏感性结果依赖所保存的五车候选 CSV；若要从零重建，需先另行执行可达性生成器并核查输出路径。
