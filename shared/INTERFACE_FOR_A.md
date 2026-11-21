# 几何接口使用说明 - 供调度模块（成员 A）使用

## 📋 接口概述

文件位置：`shared/geometry_interface.py`

**当前状态**：建筑遮挡 `check_building_occlusion()` 和综合可观测性 `check_observation_feasibility()` 均尚未实现，调用会抛出 `NotImplementedError`，不会返回正式几何结果。水平距离、仰角计算和云台范围检查已可用。

---

## 🔧 核心接口

### 1. `check_observation_feasibility()` - 综合可观测性检查

**功能**：一次性检查车辆能否观测目标，返回完整的几何信息和遮挡状态。

**接口签名**：
```python
def check_observation_feasibility(
    vehicle_position: Tuple[float, float],      # 车辆地面中心坐标 (x, y) [m]
    target_position: Tuple[float, float, float], # 目标三维坐标 (x, y, z) [m]
    buildings: Optional[list] = None            # 建筑物列表（可选）
) -> Dict
```

**输入参数**：
- `vehicle_position`: 车辆地面中心的二维坐标 `(x, y)`，单位米
- `target_position`: 目标的三维坐标 `(x, y, z)`，单位米
- `buildings`: 建筑物列表，格式见 `constants.BUILDINGS`；若为 `None`，则不检查遮挡

**返回值**：字典，包含以下字段
```python
{
    'feasible': bool,              # 是否可观测（总体判断）
    'horizontal_distance': float,  # 水平距离 [m]
    'elevation_angle': float,      # 云台仰角 [度]，正值向上仰，负值向下俯
    'occluded': bool,              # 是否被建筑遮挡
    'reason': str                  # 不可观测的原因（若不可观测）
}
```

**使用示例（仅展示预期调用形式；当前调用会抛出 `NotImplementedError`，不可用于正式结果）**：
```python
from shared.geometry_interface import check_observation_feasibility
from shared.constants import BUILDINGS, TARGETS

# 检查车辆 1 能否观测目标 1
vehicle_pos = (15.0, 14.0)
target_pos = (84.64, 70.00, 45.00)

result = check_observation_feasibility(vehicle_pos, target_pos, BUILDINGS)

if result['feasible']:
    print(f"可观测！水平距离={result['horizontal_distance']:.2f}m, "
          f"仰角={result['elevation_angle']:.2f}°")
else:
    print(f"不可观测：{result['reason']}")
```

**实现状态**：🔴 未实现（NotImplementedError）

---

### 2. `calculate_elevation_angle()` - 计算云台仰角

**功能**：计算从车辆摄像头到目标的仰角。

**接口签名**：
```python
def calculate_elevation_angle(
    vehicle_position: Tuple[float, float],
    target_position: Tuple[float, float, float]
) -> float
```

**输入输出**：
- 输入同上
- 输出：仰角 [度]，正值表示向上仰，负值表示向下俯

**注意事项**：
- 摄像头实际高度 = 车辆地面位置 + `CAMERA_HEIGHT`（2.0m）
- 云台有效范围：`-10°` 至 `+80°`（由 `is_within_gimbal_range()` 检查）

**实现状态**：✅ 已实现

---

### 3. `calculate_horizontal_distance()` - 计算水平距离

**功能**：计算车辆与目标在 xy 平面上的距离。

**接口签名**：
```python
def calculate_horizontal_distance(
    vehicle_position: Tuple[float, float],
    target_position: Tuple[float, float, float]
) -> float
```

**输入输出**：
- 输入同上
- 输出：水平距离 [m]

**实现状态**：✅ 已实现

---

### 4. `check_building_occlusion()` - 建筑遮挡检查

**功能**：检查视线是否被建筑物遮挡。

**接口签名**：
```python
def check_building_occlusion(
    vehicle_position: Tuple[float, float],
    target_position: Tuple[float, float, float],
    buildings: list
) -> Tuple[bool, Optional[int]]
```

**输入输出**：
- 输入同上
- 输出：`(是否被遮挡, 遮挡的建筑ID)`；若未被遮挡，第二个值为 `None`

**实现状态**：🔴 未实现（NotImplementedError）- 这是 P1 核心算法

---

### 5. `is_within_gimbal_range()` - 云台角度范围检查

**功能**：检查仰角是否在云台允许范围内。

**接口签名**：
```python
def is_within_gimbal_range(elevation_angle: float) -> bool
```

**输入输出**：
- 输入：仰角 [度]
- 输出：是否在范围内（`-10°` 至 `+80°`）

**实现状态**：✅ 已实现

---

## 📦 常量定义

所有常量位于 `shared/constants.py`：

```python
from shared.constants import (
    FIELD_SIZE,                  # 场地尺寸: 100m
    VEHICLE_RADIUS,              # 车辆半径: 1.5m
    VEHICLE_SPEED,               # 车辆速度: 3m/s
    CAMERA_HEIGHT,               # 摄像头高度: 2m
    GIMBAL_PITCH_MIN,            # 云台最小俯仰角: -10°
    GIMBAL_PITCH_MAX,            # 云台最大俯仰角: 80°
    GIMBAL_MAX_ANGULAR_VELOCITY, # 云台最大角速度: 30°/s
    JOINT_OBSERVATION_TIME,      # 联合观测时间: 5s
    BUILDINGS,                   # 建筑物参数列表
    INITIAL_VEHICLE_POSITIONS,   # 车辆初始位置列表
    DISPATCH_CENTER,             # 调度中心坐标
    TARGETS,                     # 目标笛卡尔坐标列表
    TARGETS_POLAR                # 目标极坐标列表
)
```

---

## 🚀 使用建议

### 当前阶段（2026-11-21）
由于建筑遮挡和综合可观测性函数尚未实现，建议成员 A：

1. **先设计调度逻辑框架**，使用接口函数的**签名**进行规划
2. **仅在联调测试中使用下方 mock**，不要把模拟值用于可观测性判定或正式调度结果。
3. **与成员 B 确认接口需求**：
   - 返回值是否满足调度需求？
   - 是否需要额外的几何信息？
   - 异常情况如何处理？

### 联调专用 mock

```python
def mock_check_observation_feasibility(vehicle_position, target_position, buildings=None):
    """仅供调度流程联调；不执行任何几何判定。"""
    return {
        "is_mock": True,
        "feasible": True,  # 固定值，仅用于走通成功分支
        "horizontal_distance": None,
        "elevation_angle": None,
        "occluded": None,
        "reason": "MOCK_ONLY: 未执行几何判定",
    }
```

此示例不是正式接口的一部分。只在测试中显式注入，不要在正式接口抛出 `NotImplementedError` 时回退到 mock，也不要将模拟结果写入正式结果。

---

## 📞 接口需求反馈

如果调度模块需要以下功能，请与成员 B 沟通：

- [ ] 批量检查多个车辆-目标组合
- [ ] 返回可观测的车辆列表
- [ ] 计算最短移动路径
- [ ] 考虑云台转动时间
- [ ] 其他几何信息（方位角、斜距等）

---

## ⚠️ 重要提醒

1. **坐标系统**：
   - 场地坐标系：x、y 范围均为 [0, 100] 米
   - 车辆坐标为地面中心位置，摄像头高度需加上 `CAMERA_HEIGHT`
   - 目标坐标的 z 值即为离地高度

2. **方位角定义**：PDF 第1页明确从正东逆时针计，第2页给出坐标转换公式；队员目前也暂定正东为 0°、逆时针为正；`TARGETS` 按该公式计算。

3. **测试数据**：
   - 参数与题面的一致性按 `test_parameters.py` 核查；该测试不是独立的 PDF 审核。
   - 建议调度模块也使用这些测试数据进行验证

---

## 📝 更新日志

- 2026-11-21：初始版本，接口框架已建立，核心函数待实现
