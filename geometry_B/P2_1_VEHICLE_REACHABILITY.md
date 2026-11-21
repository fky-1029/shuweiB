# P2(1) T2 车辆可达性分析（仅 30 s 行驶约束）

运行 `.venv/bin/python -m geometry_B.p2_vehicle_reachability`。脚本使用 `shared.constants.get_observable_points("T2")` 读取现有 CSV（26,037 个不重复点；x、y 范围各为 1.5–98.5 m），未修改可观测区域数据、P1 几何接口或 A 组调度代码。T2 可观测区域是站位候选全集；车辆初始坐标、速度 3 m/s、车半径 1.5 m、五栋建筑及 100 m 场地均来自 `shared/constants.py`。

## 判定规则与统计

每车每点先计算欧氏距离 `d=√((x−x₀)²+(y−y₀)²)`；若 `d>3×30=90 m`，因为任何合法路径长度不小于 d，可**严格证实 30 s 内不可达**。若 `d≤90 m`，连续检查起终点的车辆圆盘合法性，以及整条中心线到各建筑物闭矩形的最小距离是否至少为 1.5 m（允许相切）；矩形距离通过线段参数的有限分段二次极小值计算，**不使用稀疏采样或外扩轴对齐矩形近似**。场地为凸方形，两个端点的圆盘都在场内时整条线段亦在场内。合法直线达到欧氏距离下界，因而是最短合法路线，`path_length_m=d`、`travel_time_s=d/3≤30`，可**证实可达**。如果直线受阻则暂不判断合法绕行是否存在，状态为 `path_unverified`，路径长度与行驶时间留空；不能把它当成不可达。

| 车辆 | 总可观测点 | 距离≤90 m 候选 | 距离筛除（已证实不可达） | 已证实直达可达 | 待绕障路径验证 |
|---|---:|---:|---:|---:|---:|
| V1 | 26,037 | 22,690 | 3,347 | 10,111 | 12,579 |
| V2 | 26,037 | 21,321 | 4,716 | 8,141 | 13,180 |
| V3 | 26,037 | 24,929 | 1,108 | 12,767 | 12,162 |
| V4 | 26,037 | 24,253 | 1,784 | 8,045 | 16,208 |
| V5 | 26,037 | 24,846 | 1,191 | 18,522 | 6,324 |

数字是车—站位组合数；五车可能计入同一可观测点。三个状态互斥且每行相加为总点数。场地边界/建筑相切允许，碰撞检验沿用共享站位接口的 `1e-12 m` 浮点接触余量。对于几乎擦边而处于此量级浮点余量内的数值边界情形，可在最终站位方案中复核。

## 输出与查询

- `figures/p2_t2_reachability_summary.csv`：五车各自初筛与三态计数。
- `figures/p2_t2_v1_distance_candidates.csv` 至 `figures/p2_t2_v5_distance_candidates.csv`：每个通过 `d≤90 m` 初筛点的坐标、欧氏距离、状态、已确认路线长度和时间（未确认则空）、判定依据。距离排除点不在单车候选文件中，仍计入汇总表；原始全集由共享 CSV 提供。
- `figures/p2_t2_vehicle_reachability_v2.png`：五个同尺度小图展示全体可观测点与各车已证实直达可达点。灰色点**既可能待验证也可能被距离下界排除**，不得按灰色直接判不可达。早期布局图仅作本地过程记录；交付中使用 v2 图。

```python
from geometry_B.p2_vehicle_reachability import ReachabilityIndex
from shared.constants import get_observable_points
index = ReachabilityIndex(get_observable_points("T2"))
record = index.get(1, (10.0, 10.0))  # 只接受共享网格已有的站位
print(record.status, record.confirmed_reachable)
print(record.travel_time_s)         # 待验证或距离排除时为 None
print(record.passes_distance_screen) # 未确认的点是否满足欧氏距离必要条件
```

## A 组路径接口需求与范围

检查时 `scheduling_A/` 无路径实现；现有 `geometry_B.p2_two_station_tools.straight_line_travel_time()` 只给欧氏直线时间下界，不能用来证明绕障可达。后续需要 A 组提供例如 `route(start_xy, end_xy, vehicle_radius, buildings, field_size) -> {path_length_m, path_xy, status, shortest_certified}` 的公共接口，并明确速度模型；**有完整验证的合法路径且长度≤90 m** 可证明可达，**最短路径下界>90 m 或保证求得最短路径且最短长度>90 m** 才能证明不可达。未找到路径或普通启发式路径长度>90 m，只能保持待验证。当前脚本不接入未经核实的外部路线，不调用 RMSE，不执行车辆配对或选站优化。RMSE 为优化目标；30 s 为单车独立约束，二者不加权。
