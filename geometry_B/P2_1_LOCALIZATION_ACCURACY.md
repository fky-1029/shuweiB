# P2(1) 双站水平测向精度指标说明

调用 `geometry_B.p2_localization_accuracy.calculate_localization_metrics(station1, station2, target, sigma_deg=1.0)`。输入均为平面 `(x,y)` 坐标（米），`x` 东、`y` 北；目标 T2 的水平坐标来自 `shared.constants.TARGETS[1]`，即 `(50+45cos150°, 50+45sin150°)`，高度 35 m **不参加水平测向定位公式**。

返回字典的物理意义：

| 键 | 含义 | 单位 |
|---|---|---|
| `r1_m`, `r2_m` | 两站分别到目标水平投影的欧氏距离 | m |
| `baseline_m` | 两站间基线欧氏长度 `‖P2−P1‖` | m |
| `alpha1_deg`, `alpha2_deg` | 各站指向目标的水平测向角 `atan2(yT−yi,xT−xi) mod 360°`，正东为 0°、逆时针为正 | °，`[0,360)` |
| `gamma_deg` | 目标处两条站—目标直线（有向射线）的夹角；`atan2(|u1×u2|,u1·u2)`，`ui=(T−Pi)/ri` | °，`[0,180]` |
| `rmse_m` | 一阶误差传播的水平坐标误差均方根 `√(Var(x)+Var(y))`，非各轴的标准差之和 | m |
| `degenerate` | 当 `|sin γ|≤1e−12` 时标记数值交会退化，RMSE 置为 `inf` | 布尔值 |

## 一阶公式核验

每站测角观测方程 `αi=atan2(y−yi,x−xi)`（弧度）；在真实目标坐标处一阶线性化：`δα≈J δp`，第 i 行 `Ji=[−(yT−yi)/ri², (xT−xi)/ri²]`。若两站测角误差相互独立，同标准差 `σrad=σdeg π/180`，则 `Cov(δα)=σrad² I`；非退化时 `Cov(δp)=J⁻¹(σrad² I)(J⁻¹)ᵀ`。由于 `|det J|=|sin γ|/(r1 r2)`，计算迹得到

`RMSE=√tr(Cov(δp))=σrad √(r1²+r2²)/|sin γ|`。

该表达式假定角度误差足够小、可在真实交点附近作局部线性化；测角误差独立且同方差，站位与目标位置的系统误差、目标运动、遮挡误判和高度不确定性均未纳入。当 `σrad/|sin γ|` 不够小时，即使未触发数值退化门槛，一阶公式仍可能不可靠，输出的大 RMSE 不能视为精确的非线性误差量化。`1e−12` 是**纯数值**阈值，约对应离 0°/180° `5.73e−11°`，不是用来筛除定位质量差的正常候选站位；即使极近共线但超出门槛，函数也返回有限的线性估计。若站点与目标水平投影重合，方位角无定义，明确抛出 `ValueError`。

示例（仅演示公式，不是选站结果）：

```python
from geometry_B.p2_localization_accuracy import calculate_localization_metrics
result = calculate_localization_metrics((-20, 0), (0, -20), (0, 0))
print(result["gamma_deg"], result["rmse_m"])  # 90.0, 约 0.49365 m

from shared.constants import TARGETS
t2 = TARGETS[1]
target_xy = (t2["x"], t2["y"])
# 待队员确定可行站位后调用 calculate_localization_metrics(P1, P2, target_xy)
```

复测：`.venv/bin/python -m unittest geometry_B.test_p2_localization_accuracy -v`。本模块**只计算定位精度**；该 RMSE 是 P2(1) 的优化目标，车辆 **30 s 行驶时间是独立约束**，不是与 RMSE 加权的目标。本模块不做可观测性验证、避障路径、时间约束筛选或站位优化。
