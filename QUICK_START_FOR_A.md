# 快速上手指南 - 给成员 A

## 🚀 立即可用的函数

```python
from shared.constants import *
from shared.geometry_interface import (
    calculate_horizontal_distance,    # ✅ 计算水平距离
    calculate_elevation_angle,        # ✅ 计算仰角
    is_within_gimbal_range           # ✅ 检查云台范围
)

# 示例 1: 计算车辆1到目标1的距离
vehicle_pos = (15.0, 14.0)
target_pos = (84.64, 70.00, 45.0)

distance = calculate_horizontal_distance(vehicle_pos, target_pos)
# 结果: 89.36m

# 示例 2: 计算仰角
angle = calculate_elevation_angle(vehicle_pos, target_pos)
# 结果: 25.70°

# 示例 3: 检查云台是否可用
if is_within_gimbal_range(angle):
    print("仰角在云台范围内（不代表可观测）")
```

## 📚 详细文档

- **接口完整说明**：`shared/INTERFACE_FOR_A.md`
- **第一阶段报告**：`REPORT_2026-11-21_PHASE1.md`

## 🔴 尚未实现的功能

```python
# 以下仅为函数名称，不是可执行的零参数调用；正式调用仍抛出 NotImplementedError
# check_building_occlusion: 建筑遮挡检查（P1核心算法）
# check_observation_feasibility: 综合可观测性检查
```

## 💡 建议

1. **现在可以做**：
   - 使用已实现的 3 个基础函数设计调度框架
   - 仅在联调测试中显式使用 [可观测性 mock](shared/INTERFACE_FOR_A.md#联调专用-mock)；`is_mock: True` 的结果不得用于正式调度。
   - 设计车辆指派和路径规划算法

2. **等待 B 完成**：
   - 建筑遮挡算法（P1）
   - 综合可观测性检查

3. **如何查看这些文件**（不合并代码）：
   ```bash
   git fetch origin
   git show origin/江可萌:shared/INTERFACE_FOR_A.md
   git show origin/江可萌:shared/geometry_interface.py
   ```

## 📞 需要沟通的事项

如果调度模块需要额外功能，请告诉成员 B：
- [ ] 批量检查多个车辆-目标组合？
- [ ] 返回可观测的车辆列表？
- [ ] 计算移动路径和时间？
- [ ] 其他几何信息？

---

**更新时间**：2026-11-21
**状态**：基础函数已可用，核心算法开发中
