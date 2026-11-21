# P1 阶段成果（T1 可观测区域）

本阶段按以下三个约束的**交集**判定车辆停车位置：

1. 半径 `1.5 m` 的车辆圆盘完整位于 `100 m × 100 m` 场地内，且不侵入五栋建筑的水平投影；恰好接触允许。
2. 摄像头（离地 `2 m`）到目标的有限三维视线线段不与建筑长方体相交；与面、棱、顶点接触均计为遮挡。
3. 云台仰角处于闭区间 `[-10°, 80°]`。

按 `0.5 m` 间距采样场地坐标，共 `201 × 201 = 40401` 个网格点，其中 `22788` 个满足三项约束。**有效网格点数量不是连续区域面积**，图像仅表示本次采样结果。本段是原网格阶段的历史记录；**后续已验证达到主目标理论下界的连续可行见证，但部署时间最优站位尚未确定**，详见 `geometry_B/P1_CIRCLE_ANALYSIS.md`。

- `figures/p1_observable_region.png`：从已有 NPZ 网格绘制的论文优先图（原路径 `figures/p1_t1_observable_region_0p5m.png` 保留相同内容）。平面坐标为东向 `x`、北向 `y`（米），范围均为 `0–100 m`，等比例显示；`0.5 m` 网格采样。图例：绿色为可观测采样区域，浅红色为不可观测采样区域，灰色为五栋建筑的水平投影，红色三角形为 T1 的水平投影。图中**未标注最优站位**。T1 有效采样点为 `22788/40401`；图中颜色仅反映采样结果，不表示连续区域的精确面积或边界。
- `figures/p1_t1_observable_points_0p5m.csv`：有效采样点的东向 `x`、北向 `y` 坐标，供后续计算与复核。
- `figures/p1_t1_observable_grid_0p5m.npz`：`x_values`、`y_values`、`observable` 布尔矩阵及采样参数，`observable[j,i]` 对应 `(x_values[i], y_values[j])`，供后续计算与验证。

从项目根目录运行 `.venv/bin/python -m geometry_B.generate_region` 可重新生成；测试命令为 `.venv/bin/python -m unittest discover -s geometry_B -v`。调度模块调用方式见 `shared/INTERFACE_FOR_A.md`；接口不负责行驶路径或调度。

## 数值核验与给 C 的附图说明

运行 `.venv/bin/python -m geometry_B.p1_diagnostics` 可基于**现有** `shared/observable_points/T1_0p5m.csv`、`figures/p1_t1_observable_grid_0p5m.npz` 重新生成以下客观指标与图，不重新求解模型或更改原图。题面方位角从正东逆时针计；T1 的精确坐标约为 `(84.641016, 70, 45)` m（两位小数：`84.64, 70.00, 45.00`）。图中横轴为东向 x、纵轴为北向 y，单位 m。

- `figures/p1_t1_observable_metrics_0p5m.csv`：每个有效网格点的 `(x,y)`、水平距离 `r`（m）、仰角 `θ`（度）、指标 `Q=1/r`（m⁻¹）。**Q 只是约定的距离倒数，不是双站定位精度或优化结论**。可从原始点与 `shared/geometry_interface.py` 的距离/仰角函数逐行复算。
- `figures/p1_t1_diagnostics_0p5m.json`：网格、样本数、r/θ/Q 的 min、5% 分位数、中位数、均值、95% 分位数、max 与数值异常检查。
- `figures/p1_t1_distance_distribution_0p5m.png` / `.svg`：22,788 个有效采样点的水平距离直方图。图注建议：“T1 可观测网格点至目标的水平距离分布（0.5 m 网格，非连续区域概率分布）。”
- `figures/p1_t1_elevation_distribution_0p5m.png` / `.svg`：相同采样点的云台仰角直方图。图注建议：“T1 可观测网格点的目标仰角分布（摄像头离地 2 m，0.5 m 网格）。”
- `figures/p1_t1_observable_region_0p5m.svg`：现有区域数据的矢量版本；绿色可观测，浅红色不可观测，灰色建筑，红色三角形 T1。图注建议：“T1 可观测位置采样区域，绿色表示采样点满足三项静态约束；图中未给出最优站位。”
- `figures/p1_t1_boundary_checks_0p5m.csv`：固定种子 `20261121` 从四邻类别变化的网格点抽取 60 点，与综合判定复核，并在每点 `(x+0.125,y+0.125)` m（必要时限制在场地内）作连续坐标判定；这些离散边缘样本**不是连续可观测区域的精确边界**。

绘图调用方可用 `geometry_B.observable_region_plot.plot_field(observable=mask, x_values=x, y_values=y, candidate_positions=..., boundary_positions=..., optimal_position=...)` 叠加**明确提供**的点；默认不绘制任何候选/最优点。后续已验证主目标的理论最优值，仍不得将网格最小距离点直接宣称为**部署时间**最终最优站位。

## 给 C：圆周并列站位补充分析（新增）

- 数学证明与规则：`geometry_B/P1_CIRCLE_ANALYSIS.md`。主目标 `Q=1/r` 的距离下界 `43/tan80°=7.582060170463998 m`，且 `(80.00207316612234,75.99731976870402)` 通过共享可行性接口达到下界；这是**主目标最优值证明**，不表示部署时间最优。
- `figures/p1_t1_circle_candidates_1deg.csv`：360 个每 1° 采样圆周点的原始及修正后可行性、失败原因、两类单独净空。**262 个原始点**直接合法；31 个点为临界角度的机器精度修正，其中 22 个变为合法，最终得到 **284 个**严格接口判为合法的数值采样点；最大修正距离 `1.33e-14 m`。
- `figures/p1_t1_vehicle_deployment_1deg.csv`：284 点×5 车的初筛对比，标注 `straight_line_lower_bound`；已标出每站最快下界车辆，不能当作实际避障部署时间。
- `figures/p1_t1_circle_candidates_1deg.png` / `.svg`：圆周可行样本及直线时间下界最小点图。该星号站位的直达路径后来通过连续避障检验，因此**可证明为 1° 离散集合内的部署时间最优点**，但非连续圆周全局最优。横轴东 x、纵轴北 y，单位 m；绿色样本为圆周数值近似，底图来自原 0.5 m 网格。
- `figures/p1_t1_circle_summary_1deg.json`：主目标可行见证、浮点修正审计及原初筛记录。V4、260° 样本 `(83.32440521981547,62.53312836032199)` 的直线时间下界为 `5.06453312743745 s`，通视净距 `4.324405219815475 m`，停车净空 `2.8244052198154748 m`；后来经 `geometry_B.p2_vehicle_reachability.straight_path_is_legal()` 验证其直线路径合法，故该值是离散集合内可达到的实际部署时间最优。JSON 的路径状态字段仍记录导出时尚未核查的历史状态；连续圆周最优未证明。

复算命令：`.venv/bin/python -m geometry_B.p1_circle_analysis`；相关测试：`.venv/bin/python -m unittest geometry_B.test_p1_circle_analysis -v`。题面方位角仍统一为正东逆时针；圆周采样角是以 T1 水平投影为圆心的局部参数角，勿与告警方位混淆。
