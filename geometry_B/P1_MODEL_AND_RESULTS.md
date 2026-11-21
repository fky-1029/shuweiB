# P1 模型、计算过程与已验证网格结果（T1）

> 本文记录 **0.5 m 离散网格阶段**的可复核计算与数学推导。`(80,76)` 是已验证的**网格最优候选**。**后续更新（圆周阶段）**：理论下界已由一个连续可行见证点达到，故主目标最优值已证实；详见 `geometry_B/P1_CIRCLE_ANALYSIS.md`。网格点仍不应称为连续全局最优站位。

## 1. 原始数据、坐标与约束

场地为 `[0,100] × [0,100]` m，`x` 向东、`y` 向北。原题方位角从正东逆时针计；T1 从 `(50,50)` 以 `R=40 m`、方位角 `30°` 计算得 `(50+40cos30°, 50+40sin30°, 45) = (84.64101615137756,70,45)` m。摄像头高度 `h_c=2 m`、车辆半径 `a=1.5 m`，高度差 `Δh=43 m`。所有约束的实际布尔判定均调用已验证的 `shared.geometry_interface.check_observation_feasibility()`，本文不另写遮挡或碰撞算法：

1. **停车合法性**：车辆中心在 `[a,100-a]²` 内；车辆圆盘不得进入任一建筑水平投影，允许车辆与建筑/场地边界恰好接触。对轴对齐矩形，检查车中心到矩形的最近欧氏距离是否至少为 `a`。
2. **有限三维视线无遮挡**：摄像头 `(x,y,2)` 到目标 `(x_T,y_T,45)` 的闭线段与五个建筑的三维长方体不能相交；接触面、棱或顶点亦按遮挡处理。**Slab 原理**：令 `P(t)=P_0+t(P_1-P_0)`、`t∈[0,1]`。对建筑每一坐标轴的闭区间，分别求线段满足该轴约束的参数区间；方向分量为零时，若常量坐标在轴区间外则没有交，否则该轴不收缩参数区间。三轴区间与 `[0,1]` 交集非空即视为与闭长方体相交（遮挡）。既有接口负责数值处理与边界语义。
3. **云台仰角**：`θ=atan2(45−2, r)`，其中 `r=√((x−x_T)²+(y−y_T)²)`；应满足 `−10° ≤ θ ≤ 80°`（本题 T1 高于摄像头，实际 θ 为正）。

## 2. 目标函数及等价变换

对 `r>0`，题设指标为 `Q(x,y)=1/r(x,y)`（m⁻¹）；`dQ/dr=−1/r²<0`，故在**同一个可行域**内 `argmax Q = argmin r`。这只说明水平距离指标的单调等价，不意味着无遮挡或可停车等约束可忽略，也不等于双站定位精度。在 `r=0` 的形式上 Q 未定义；实际 T1 可行采样点的最小距离严格大于零。

仰角上界 `θ≤80°` 且 `Δh=43>0`，由 `tan θ=43/r`（`r>0`）及单调性得到必要条件

`r ≥ 43/tan(80°) ≈ 7.582060170464 m`。

这是**仅由云台约束推出的理论下界**。在本报告原网格阶段，尚未验证其可达性；**后续已在 `geometry_B/P1_CIRCLE_ANALYSIS.md` 中用公共综合接口核验一个达到下界的连续可行见证**，证明主目标最优值可达到。不要把这个网格阶段的“未验证”陈述误当成当前结论。

## 3. 规则网格、复算和数据来源

用 `x_i=0.5i`、`y_j=0.5j` m（`i,j=0,…,200`）对 40,401 个格点逐一调用综合可行性接口。网格原始矩阵位于 `figures/p1_t1_observable_grid_0p5m.npz`，`observable[j,i]` 与 `(x_i,y_j)` 对应。有效点在 `shared/observable_points/T1_0p5m.csv`；另有 `figures/p1_t1_observable_points_0p5m.csv` 作历史复核。数据表 `figures/p1_t1_observable_metrics_0p5m.csv` 对 **22,788** 个有效点逐行给出 `x,y,r,θ,Q`；由 `geometry_B.p1_diagnostics` 使用公共 `calculate_horizontal_distance()`、`calculate_elevation_angle()` 重新计算，并核对 CSV、原网格、去重、坐标范围、所有有效点的综合可行性及有限数值。分布统计和抽样边界复核在 `figures/p1_t1_diagnostics_0p5m.json`、`figures/p1_t1_boundary_checks_0p5m.csv`；边界抽样不能证明连续边界形状。

`geometry_B.p1_optimal_station.verify_grid_candidate()` 重新运行全量审计，并扫描全量指标表的 `r`，确认 **唯一网格距离最小点**为 `(80,76)` m；公共综合接口再次确认该点可行。对其计算：

| 状态 | 网格站位 `(x,y)` m | `r` m | `θ` ° | `Q=1/r` m⁻¹ |
|---|---:|---:|---:|---:|
| 已验证的 0.5 m 网格最优候选 | `(80,76)` | `7.58544862993` | `79.9956212159` | `0.131831358801` |

差值 `r_grid − 43/tan80° ≈ 0.003388459469 m` 只是此网格候选与云台必要下界的差，**不是连续最优性误差界**。`figures/p1_t1_grid_candidate_0p5m.json` 保存机器可读复核结果，明确 `continuous_global_optimum_established=false`。当前区域图不因这个候选而被覆盖或擅自改标为最终解。

## 4. 可复现运行与待验证结论

从项目根目录用项目环境执行：

```bash
.venv/bin/python -m geometry_B.p1_optimal_station
.venv/bin/python -m unittest geometry_B.test_p1_optimal_station -v
```

仅需单点检查时，`from geometry_B.p1_optimal_station import validate_continuous_candidate`；`validate_continuous_candidate((x,y))` 调用同一个综合可行性接口并报告 `r,θ,Q`，**不搜索**、不选择部署时间最优站位。后续连续见证已证明主目标值可达到，但连续圆周上的部署时间严格最优仍未证明；详见 `geometry_B/P1_CIRCLE_ANALYSIS.md`。
