# P2(1) 双站交会定位结果说明卡

> 用途：交给 C 整理进论文。定位精度 RMSE 是优化目标；车辆行驶时间不超过 30 s、可观测性及连续路径合法性是约束，不构造“精度 + 时间”的加权目标。

- **模型名称/类型：**
  双站独立同方差方位测量的一阶误差传播模型；在通过观测与路径约束的离散站位对中最小化水平定位 RMSE。

- **核心公式（LaTeX）：**
  T2 平面坐标由告警中心 `(50,50)`、距离 `45 m` 和方位 `150°` 得
  \[
  (x_T,y_T)=\left(50+45\cos150^\circ,\;50+45\sin150^\circ\right)
  =(11.0288568297,72.5)\ \mathrm m.
  \]
  对站位 `P_i=(x_i,y_i)`，`r_i=\|T-P_i\|`，方位角
  \[
  \alpha_i=\operatorname{atan2}(y_T-y_i,x_T-x_i).
  \]
  交会角 `\gamma\in[0^\circ,180^\circ]`，两站误差独立且标准差同为 `\sigma_{\rm rad}=\sigma_{\rm deg}\pi/180` 时，
  \[
  \operatorname{RMSE}=\sigma_{\rm rad}
  \frac{\sqrt{r_1^2+r_2^2}}{|\sin\gamma|}.
  \]
  其一阶依据是测角方程雅可比 `J_i=[-(y_T-y_i)/r_i^2,\;(x_T-x_i)/r_i^2]`，且
  \[
  \operatorname{Cov}(\hat T)\approx J^{-1}(\sigma_{\rm rad}^2 I)(J^{-1})^\mathsf T,
  \qquad \operatorname{RMSE}=\sqrt{\operatorname{tr}(\operatorname{Cov}(\hat T))}.
  \]

- **为什么这么建（一句话原理）：**
  两个独立方位观测在交会点附近线性化后，通过雅可比逆矩阵把角度噪声传播到平面坐标协方差，以协方差迹的平方根衡量水平定位精度。

- **参数来源（题目给/自己定/数据估计 + 理由）：**
  T2 告警方位、水平距离、高度、中心坐标以及测角误差 `N(0,(1°)^2)` 来自题目；T2 坐标按正东为零、逆时针为正计算。建筑、场地、车辆速度、车辆尺寸、相机和云台参数复用 `shared/constants.py`。可观测位置文件 `shared/observable_points/T2_0p5m.csv` 提供 `0.5 m` 网格候选；网格分辨率是数值离散化设置，不是连续精度证明。

- **算法（名称、为什么选、关键参数、初始值、停止条件）：**
  使用有限网格上的双站组合枚举及分层可行性筛选，不使用连续优化器。先从 26,037 个 T2 可观测网格站位构造候选站位对，再筛选两站不同、几何非退化、两车各自路径合法且行驶时间 `≤30 s` 的组合；对剩余组合用一阶 RMSE 排序。有限枚举无初始值或迭代停止条件。最终结果另报告名义最优与仰角敏感性情景，不能混称一个解。

- **结果数值（带单位）：**
  - T2 平面目标坐标 `(11.02885682970026,72.5) m`，目标高度 `35 m`。
  - 两站独立测角标准差 `1°`；所有结果的精度单位为 `m`。
  - 论文引用的离散网格名义最优、对应站位坐标、RMSE、交会角、各车行驶时间和仰角敏感性数值，**请以** `geometry_B/P2_1_FINAL_PAPER_RESULTS.md` 及其列出的生成 CSV 为准，转录时保留其情景限定，不在本卡重复手抄可能过期的长小数。
  - 目前证明范围为既定 `0.5 m` 网格与一阶误差模型内；连续空间全局最优未证明。

- **评价指标：**
  主优化指标为水平 RMSE（m），越小越好；这是两个平面坐标误差方差之和的平方根。车辆行驶时间上限 `30 s`、可观测性、两站不同及非退化、车辆圆盘连续路径合法性均是独立约束，不加权进入 RMSE。若报告仰角余量敏感性方案，应说明它是额外情景条件下的解，而非原始名义目标的无条件最优解。

- **图（文件名 + 每张图说明什么）：**
  - `figures/p2_intersection_geometry.png`：已提交的双站测向射线及交会几何论文图。
  - `figures/p2_accuracy.png`：P2(1) 定位精度相关图；结果数据与情景含义以 `P2_1_FINAL_PAPER_RESULTS.md` 和相邻 CSV 说明为准。
  - `figures/p2_t2_intersection_degeneracy_final.png`：本地过程示意，**未作为正式论文图提交**；论文中交会角退化说明优先使用 `figures/p2_accuracy.png`，并以 `geometry_B/P2_1_FINAL_PAPER_RESULTS.md` 核对图意。

- **验证/检验（怎么证明模型对）：**
  1. `geometry_B/p2_localization_accuracy.py` 的单元测试以正交测向、共线退化、交换站位和误差翻倍检查距离、交会角及 RMSE 性质。
  2. 通过方位观测雅可比与协方差传播独立计算 RMSE，与解析公式交叉核验。
  3. 站位优化、路径可达性及最终情景分析分别由 `geometry_B/test_p2_two_station_optimize.py`、`geometry_B/test_p2_vehicle_reachability.py`、`geometry_B/test_p2_final_analysis.py` 覆盖。建议复核：`.venv/bin/python -m unittest geometry_B.test_p2_final_analysis geometry_B.test_p2_two_station_optimize geometry_B.test_p2_vehicle_reachability geometry_B.test_p2_localization_accuracy -v`。
  4. 网格穷举最优只对存档网格、当前路径约束与当前误差模型成立；不能据此声称连续空间全局最优。

- **本问结论一句话：**
  在 T2 的既定 `0.5 m` 可观测网格、双站一阶独立测角误差模型及各车 `30 s` 合法路径约束下，可报告离散集合内 RMSE 最优结果；连续空间最优性未证明，仰角余量情景须与名义最优分开报告。
