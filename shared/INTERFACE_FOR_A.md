# 几何接口交接（供 A 调用）

从项目根目录执行 Python，可直接导入 `shared.geometry_interface`。本模块只判断**给定停车位置和静止目标**的几何可观测性，不负责车辆行驶路径规划、到达时间、调度或最优站位。

```python
from shared.constants import TARGETS
from shared.geometry_interface import check_observation_feasibility

target = TARGETS[0]
result = check_observation_feasibility(
    (15.0, 14.0),
    (target['x'], target['y'], target['z']),
)
# result: feasible(bool)、horizontal_distance(float, m)、
# elevation_angle(float, 度)、occluded(bool)、reason(str)
```

`buildings=None` 使用 `constants.BUILDINGS`，传入 `[]` 则不检查建筑（仅用于有意忽略建筑的独立测试）。`reason` 在可观测时为空字符串，不可观测时描述违反的约束；若存在多个失败原因，用中文分号连接。车辆位置为地面圆盘中心 `(x,y)`，目标为 `(x,y,z)`；摄像头高度自动取 `CAMERA_HEIGHT`。

| 函数 | 输入 | 输出 |
| --- | --- | --- |
| `is_vehicle_position_valid(vehicle_position, buildings=None, field_size=FIELD_SIZE, vehicle_radius=VEHICLE_RADIUS)` | 车辆中心、建筑及可选场地参数 | `bool`：圆盘不越界且不侵入建筑，恰好接触合法 |
| `check_building_occlusion(vehicle_position, target_position, buildings)` | 车辆中心、目标三维坐标、建筑列表 | `(bool, Optional[int])`：有限视线是否接触/穿过建筑及第一栋建筑 ID |
| `calculate_horizontal_distance(vehicle_position, target_position)` | 同上前两项 | `float`：水平距离（米） |
| `calculate_elevation_angle(vehicle_position, target_position)` | 同上前两项 | `float`：相对摄像头的仰角（度） |
| `is_within_gimbal_range(elevation_angle)` | 仰角（度） | `bool`：是否在闭区间 `[-10°,80°]` 内 |
| `check_observation_feasibility(vehicle_position, target_position, buildings=None)` | 车辆中心、目标三维坐标、可选建筑列表 | 包含 `feasible`、`horizontal_distance`、`elevation_angle`、`occluded`、`reason` 的字典 |

综合判断同时要求车辆停车合法、视线未被遮挡、仰角在云台范围内。建筑与目标参数见 `shared/constants.py`；可使用 `python3 -m unittest discover -s geometry_B -v` 检查约束测试。当前图和数据仅为 0.5 m 网格采样结果，不能代替连续区域边界证明或路线规划。
