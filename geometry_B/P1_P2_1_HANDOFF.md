# P1、P2(1) 成果交接（供 A、C 使用）

**先看这里，不必遍历全部源代码。**本文只列本组正式成果与复现入口；`figures/` 内未列出的旧版、诊断或过程图表留在本地供追溯，不作为论文优先版本。场地和目标参数取自 `shared/constants.py`，静态几何判定取自 `shared/geometry_interface.py`。坐标 x 向东、y 向北，单位为米。

## P1：T1 单站观测

三项静态约束：①车体圆盘位于场地内且不侵入建筑水平投影；②摄像头至目标的有限三维视线无遮挡（接触也算遮挡）；③云台仰角处于 `[-10°,80°]`。`geometry_B/generate_observable_points.py` 调用公共接口对 0.5 m 网格逐点判定；T1 共 22,788 个合法网格点。目标质量 `Q=1/r`，其中 r 是站位到 T1 的水平距离。由相机和目标高度差 43 m 与仰角上限推得 `r≥43/tan80°=7.582060170463998 m`；公共接口已验证连续坐标 `(80.00207316612234,75.99731976870402)` 达到此下界，故**连续空间中的观测质量最优值**已证实（按当前几何模型）。

在同质量圆周的 **1° 离散采样**中，V4 → `(83.32440521981547,62.53312836032199)` 的直线距离/速度为 `2.397866460770781 s`，云台指向时间为 `2.6666666666666687 s`，合计 `5.06453312743745 s`。这原本是所有 1420 组车—采样站位的部署时间下界最小值；进一步以 `geometry_B.p2_vehicle_reachability.straight_path_is_legal()` 核验 V4 的整条直达路径合法，故该下界可达，**可证明是该离散集合内的实际部署时间最优值**。其他候选的 CSV 时间仍只表示下界，不能笼统当作实际路线时间。并列时间（容差 `1e-9 s`）再依次以视线三维净距、车辆圆盘停车净空降序比较。1° 采样不证明连续圆周上的部署时间全局最优性。

## P2(1)：T2 双站测向交会

两站独立观测目标方位角，在目标附近线性化；单站测角标准差为 `σ=1°`。设两站到目标水平距离为 `r₁,r₂`、交会角为 `γ`，水平位置的一阶误差为 `RMSE=σ_rad√(r₁²+r₂²)/|sinγ|`。站位须满足静态可观测条件；每车**已验证合法直线路径**的行驶时间不超过 30 s，时间是可行性约束而非 RMSE 权重。

代表性的 **0.5 m 离散网格已证实可达集合最优**：V1 → `(8.0,67.5)`、V3 → `(6.0,75.5)`；行驶时间分别 `17.9853335310 s`、`4.4001262608 s`；基线 `8.2462112512 m`；交会角 `89.6122064436°`；`RMSE=0.14441638392829942 m`。V1–V5 也有**完全相同的最小 RMSE 数值**（两站与时间不同），所以最优车辆组合不唯一。`γ→0°` 或 `180°` 时近共线退化，固定距离下 `90°` 最稳。名义解两站仰角为 `79.95444°`、`79.93783°`，贴近 80° 上限：把站位约束重新筛成 `≤79.5°`、`≤79°` 后，离散最优 RMSE 分别为 `0.15114537 m`、`0.15855082 m`。这两项是**附加仰角余量情景**，不可冒充名义最优值。几何下界与待验证站位审计未发现现有网格上严格更优方案；`path_unverified` **不是不可达**。P2 连续空间全局最优性尚未证明。

## 给 C：论文与表图的最短路径

| 优先阅读/直接引用 | 内容与使用边界 |
|---|---|
| `geometry_B/P1_CIRCLE_ANALYSIS.md`；`geometry_B/P1_PHASE_RESULTS.md` | P1 连续观测质量证明、圆周初筛规则；0.5 m 可观测区域的采样解释。P1 连续圆周最优性仍需另证；其他候选的下界也不可写成实际行驶时间。 |
| `geometry_B/P2_1_FINAL_PAPER_RESULTS.md`；`geometry_B/P2_1_TWO_STATION_OPTIMIZATION.md` | P2 数学结果、退化与仰角敏感性；仅声称离散网格最优。 |
| `figures/p1_observable_region.png`；`figures/p1_t1_circle_candidates_1deg.png` | T1 正式区域图；圆周 1° 离散集合部署时间最优点图（已核验该点直达路径合法，非连续圆周最优）。 |
| `figures/p2_intersection_geometry.png`；`figures/p2_accuracy.png` | P2 名义最优布局图；固定目标距的交会角退化示意图（后者不是站位可行域优化）。 |
| `figures/p1_t1_circle_summary_1deg.json`；`figures/p1_t1_circle_candidates_1deg.csv` | P1 原值、360 个圆周样本及可行性。 |
| `figures/p2_t2_pair_optima_v2.csv`；`figures/p2_t2_optimum_summary_v2.json`；`figures/p2_t2_pitch_sensitivity.csv` | 十组车对、代表最优与三档仰角对比的正式数值；以 CSV/JSON 精确值为准。 |

**不要混淆** `figures/p1_t1_observable_region_0p5m.png`（此前的文件路径，内容与规范名图相同）或 `figures/p2_t2_*layout*.png` / `*degeneracy*.png`（旧图）与上表的论文主图。附加的 P1 诊断直方图仅作辅助，不是必须的正文图。

## 给 A：P2(2) 输入、接口与尚缺内容

- `shared/INTERFACE_FOR_A.md` 是公共接口说明；`shared/constants.py` 提供场地、建筑、车位、车辆速度和目标三维坐标；`shared/geometry_interface.py` 的 `check_observation_feasibility` 同时检查停车、视线和仰角。`shared/constants.py:get_observable_points("T1"/"T2"/"T3")` 可读 `shared/observable_points/T{1,2,3}_0p5m.csv`；不要删除这三份共享数据。
- `geometry_B/p2_vehicle_reachability.py:ReachabilityIndex` 提供车—站位距离筛选、已证实直达与未验证绕行状态；本组正式输入 `figures/p2_t2_v{1..5}_distance_candidates.csv`、`figures/p2_t2_reachability_summary.csv`。**仅 `confirmed_reachable` 表示已验证可达**；`path_unverified` 仍需 A 的合法路径/最短路验证。直线距离小于 90 m 只是绕行可能性的必要条件，不能当作实际行驶时间。
- `geometry_B/p1_circle_analysis.py:run(travel_time=...)` 留有 `(起点,终点)→秒` 的实际路径时间注入接口；应先核对路径避障、速度与单位。P2(1) 已有名义最优布局可作 P2(2) 的输入方案，但不替代 A 的路由与调度。

## 复核与文件范围

在仓库根目录、安装好项目依赖后运行：

```bash
.venv/bin/python -m unittest discover -s geometry_B -p 'test_*.py' -v
.venv/bin/python -c 'from shared.constants import get_observable_points; print({t: len(get_observable_points(t)) for t in ("T1", "T2", "T3")})'
```

第一条是回归测试，**不运行原大规模优化**；第二条应输出 `{'T1': 22788, 'T2': 26037, 'T3': 22265}`。精度模型的专项测试可运行 `.venv/bin/python -m unittest geometry_B.test_p2_localization_accuracy -v`。P1 圆周分析和 P2 全量优化的脚本会写出同名成果（独占创建或覆盖），**不要在已有成果目录直接重跑以免冲突**。需完整重生成时先备份，再按源文件的输出约定选择新路径。

实现导航：`geometry_B/observable_region_plot.py`（可观测区域图）；`geometry_B/p1_circle_analysis.py`（P1 最优圆周与下界）；`geometry_B/p2_localization_accuracy.py`（RMSE 指标）；`geometry_B/p2_two_station_optimize.py`（网格精确搜索）；`geometry_B/p2_final_analysis.py`（仰角、退化与几何松弛核查）；对应 `geometry_B/test_*.py` 是单元测试。P1 网格中间数据 `figures/p1_t1_observable_grid_0p5m.npz`、`figures/p1_t1_observable_points_0p5m.csv` 可复用，五车候选 CSV 是离线复算 P2 搜索的必需输入。文件未移动或删除；未入交付清单的过程图表仍保留本地，不影响 A、C 使用。
