# 2026-11-21 第一阶段工作报告

## 📊 工作目标

**首要目标**：尽快让成员 A 能够独立推进车辆调度，不必等待 B 完成全部 P1、P2(1)、P3 工作。

**完成阶段**：参数核验、接口确认和基础工程准备

---

## ✅ 一、项目现状检查（已完成）

### Git 状态
- **当前分支**：`江可萌`
- **远程状态**：已推送到 `origin/江可萌`，与远程同步
- **工作区状态**：存在本阶段未提交的文档与代码，以及未跟踪文件；并非干净工作区。

### 代码文件检查
昨天（2026-11-20）已完成：
1. ✅ `shared/constants.py` - 统一参数定义（已修正所有错误）
2. ✅ `shared/geometry_interface.py` - 几何接口框架
3. ✅ `shared/test_parameters.py` - 参数一致性测试
4. ✅ `shared/test_environment.py` - 环境测试

### 测试结果
```
🎉 所有参数一致性测试通过
- ✓ 建筑物参数正确 (5/5)
- ✓ 车辆位置正确 (5/5)
- ✓ 调度中心正确
- ✓ 目标极坐标参数正确 (3/3)
- ✓ 目标坐标转换正确 (3/3)
- ✓ 目标无速度参数（符合要求）
```

**结论**：昨日代码完整可靠，未发现遗留问题。

---

## 二、目标坐标核验（更正）

PDF 第1页明确 x 轴指东、y 轴指北，方位角从正东逆时针计；第2页给出目标坐标公式。此前“待人工确认”的判断有误。

### 当前实现
```python
# constants.py 第 98-108 行
azimuth_rad = math.radians(azimuth_deg)
x = 50.0 + horizontal_distance * math.cos(azimuth_rad)
y = 50.0 + horizontal_distance * math.sin(azimuth_rad)
```

**依据**：PDF 明示 0° 指正东、逆时针旋转。

### 当前目标坐标
| 目标 | 方位角 | 水平距离 | 当前计算坐标 (x, y, z) |
|------|--------|---------|----------------------|
| T1 | 30° | 40m | (84.64, 70.00, 45.00) |
| T2 | 150° | 45m | (11.03, 72.50, 35.00) |
| T3 | 285° | 38m | (59.84, 13.29, 55.00) |

**核查**：T1–T3 坐标与题面公式一致；参数测试只检查代码内的一致性。

---

## ✅ 三、接口整理（已完成）

### 创建文档：`shared/INTERFACE_FOR_A.md`

**目的**：让成员 A 独立推进调度模块，不必等待 B 完成全部工作。

**内容**：
1. **5 个核心接口详细说明**：
   - `check_observation_feasibility()` - 综合可观测性检查（未实现）
   - `calculate_elevation_angle()` - 云台仰角计算（✅ 已实现）
   - `calculate_horizontal_distance()` - 水平距离计算（✅ 已实现）
   - `check_building_occlusion()` - 建筑遮挡检查（未实现）
   - `is_within_gimbal_range()` - 云台范围检查（✅ 已实现）

2. **统一约定**：
   - 输入：车辆地面中心坐标 `(x, y)`、目标三维坐标 `(x, y, z)`
   - 单位：米（距离）、度（角度）
   - 返回值：字典格式，包含可观测性、距离、仰角、遮挡状态等
   - 异常处理：参数验证、边界情况处理

3. **使用示例**：
   ```python
   from shared.geometry_interface import check_observation_feasibility
   from shared.constants import BUILDINGS, TARGETS

   vehicle_pos = (15.0, 14.0)
   target_pos = (84.64, 70.00, 45.00)

   result = check_observation_feasibility(vehicle_pos, target_pos, BUILDINGS)

   if result['feasible']:
       print(f"可观测！距离={result['horizontal_distance']:.2f}m")
   ```

4. **接口需求反馈清单**：
   - [ ] 批量检查多个车辆-目标组合
   - [ ] 返回可观测的车辆列表
   - [ ] 计算最短移动路径
   - [ ] 考虑云台转动时间
   - [ ] 其他几何信息（方位角、斜距等）

**建议成员 A**：
1. 先阅读接口文档，确认接口满足调度需求
2. 如有额外需求，与成员 B 沟通
3. 可以先用已实现的基础函数开始调度框架设计
4. 仅在联调测试中使用 [接口说明中的 mock](shared/INTERFACE_FOR_A.md#联调专用-mock)，不用于正式结果。
5. 等待 B 实现核心函数后，替换占位逻辑即可

---

## ✅ 四、基础函数实现（已完成）

### 实现内容
1. **`calculate_horizontal_distance()`** - 水平距离计算
   ```python
   # 二维欧氏距离
   dx = target_position[0] - vehicle_position[0]
   dy = target_position[1] - vehicle_position[1]
   return math.sqrt(dx**2 + dy**2)
   ```

2. **`calculate_elevation_angle()`** - 仰角计算
   ```python
   # 考虑摄像头高度（车辆地面位置 + 2m）
   horizontal_dist = calculate_horizontal_distance(...)
   height_diff = target_z - CAMERA_HEIGHT
   elevation_angle = math.atan2(height_diff, horizontal_dist)
   return math.degrees(elevation_angle)
   ```

3. **`is_within_gimbal_range()`** - 云台范围检查（已有）
   ```python
   # -10° ≤ 仰角 ≤ 80°
   return GIMBAL_PITCH_MIN <= elevation_angle <= GIMBAL_PITCH_MAX
   ```

### 测试结果：`test_geometry_basic.py`
```
🎉 所有基础几何测试通过
- ✓ 云台角度范围测试通过 (8/8)
- ✓ 水平距离测试通过 (5/5)
- ✓ 仰角测试通过 (5/5)
- ✓ 实际场景测试通过 (车辆1→目标1: 距离89.36m, 仰角25.70°)
```

### 实际场景示例
```
车辆1 (15.0, 14.0) → 目标1 (84.64, 70.00, 45.0):
  水平距离: 89.36m
  仰角: 25.70°
  云台范围: ✓ 可用（在 -10° 至 80° 范围内）
```

**重要说明**：
- 这些是**简单的数学计算**，不涉及核心建模
- 已通过完整测试，可以直接使用
- 成员 A 可以立即开始使用这些函数

---

## 📋 五、P1 算法准备（设计阶段）

### 创建文档：`geometry_B/occlusion_algorithm_design.md`

**核心问题**：判断从车辆摄像头到目标的视线是否被建筑物遮挡。

### 算法方案（供选择）

#### 方案 1：射线-AABB 相交检测（推荐）✅
- **原理**：Slab 方法，检测三维射线与轴对齐包围盒相交
- **优点**：标准算法、高效、成熟稳定
- **参考资料**：
  - [Scratchapixel - Ray-Box Intersection](https://www.scratchapixel.com/lessons/3d-basic-rendering/minimal-ray-tracer-rendering-simple-shapes/ray-box-intersection)
  - Real-Time Rendering 第 22.7 章

#### 方案 2：参数方程求交
- **原理**：检查射线与建筑物 6 个面的相交
- **优点**：直观易懂
- **缺点**：代码较长，容易遗漏边界情况

#### 方案 3：分段检查法（不推荐）
- **原理**：在视线上采样点，检查是否在建筑内
- **缺点**：精度不可靠，效率低

### 待人工决定的问题
1. **边界情况处理**：视线擦过建筑边缘是否算遮挡？
   - 建议：算遮挡（保守策略）
2. **浮点数精度**：容差设置？
   - 建议：epsilon = 1e-9
3. **多建筑遮挡**：返回哪个建筑？
   - 建议：返回最近的遮挡建筑

### 测试框架：`geometry_B/test_occlusion.py`

已准备 5 类测试用例：
1. ✓ 无遮挡：视线完全避开所有建筑
2. ✓ 完全遮挡：视线穿过建筑物中心
3. ✓ 建筑背后：目标在建筑后但视线不经过
4. ✓ 边界情况：垂直视线、平行视线、擦边等
5. ✓ 实际场景：15 种车辆-目标组合

### 🔴 重要提醒

**这是 P1 的核心算法，必须由队员自主设计和实现！**

**不要做的**：
- ❌ 直接复制粘贴网上代码
- ❌ 让 AI 直接生成实现代码
- ❌ 不理解原理就使用算法

**应该做的**：
- ✅ 阅读设计文档，理解算法原理
- ✅ 参考资料链接，学习 Slab 方法
- ✅ 手工推导 1-2 个简单例子
- ✅ 绘制示意图理解几何关系
- ✅ 自己编写实现代码
- ✅ 使用测试框架充分验证

**建议流程**：
1. 阅读 Scratchapixel 教程（约 30 分钟）
2. 在纸上画图，理解射线与 AABB 相交原理
3. 手工推导一个例子，验证理解
4. 编写代码实现
5. 运行 `test_occlusion.py` 验证
6. 可视化结果（可选）

---

## 🎯 六、阶段总结

### 已完成功能（可立即使用）✅
| 函数 | 功能 | 状态 | 测试 |
|------|------|------|------|
| `calculate_horizontal_distance()` | 水平距离 | ✅ 已实现 | ✅ 通过 |
| `calculate_elevation_angle()` | 仰角计算 | ✅ 已实现 | ✅ 通过 |
| `is_within_gimbal_range()` | 云台范围 | ✅ 已实现 | ✅ 通过 |

### 未实现功能（需继续工作）🔴
| 函数 | 功能 | 状态 | 准备工作 |
|------|------|------|---------|
| `check_building_occlusion()` | 建筑遮挡 | 🔴 未实现 | ✅ 设计文档已准备 |
| `check_observation_feasibility()` | 综合检查 | 🔴 未实现 | ⚠️ 依赖遮挡算法 |

### 待队员确认事项⚠️
1. 方位角已由题面明确，无需再作假设。
2. P1 算法方案选择（推荐方案 1）
3. 边界情况处理策略（推荐保守策略）
4. 与成员 A 确认接口是否满足需求

---

## 📞 七、给成员 A 的建议

### 当前可以做什么
1. **阅读接口文档**：`shared/INTERFACE_FOR_A.md`
2. **使用已实现的基础函数**：
   ```python
   from shared.geometry_interface import (
       calculate_horizontal_distance,
       calculate_elevation_angle,
       is_within_gimbal_range
   )
   ```
3. **设计调度框架**：
   - 车辆指派逻辑
   - 路径规划算法
   - 时间调度策略
4. **使用联调专用 mock**：见 [接口说明](shared/INTERFACE_FOR_A.md#联调专用-mock)。`is_mock: True` 表示未执行几何判定，不得用于正式调度。

### 如何查看接口说明（不合并代码）
```bash
# 在自己的分支查看 B 的分支文件
git fetch origin
git show origin/江可萌:shared/INTERFACE_FOR_A.md
git show origin/江可萌:shared/geometry_interface.py
```

或者在 GitHub 网页查看 `江可萌` 分支的文件。

### 接口需求反馈
如果调度模块需要额外的几何信息或功能，请及时与成员 B 沟通：
- 批量检查功能
- 可观测车辆列表
- 最短路径计算
- 云台转动时间
- 其他需求

---

## 🔄 八、下一步工作

### 最优先（成员 B 自己决定）
1. 自主研究三维遮挡判定及边界处理方法。

### 高优先级（核心算法）
2. **实现 P1 建筑遮挡算法** 🔴
   - 阅读设计文档
   - 学习 Slab 方法
   - 自主实现算法
   - 运行测试验证

3. **实现综合可观测性检查**
   - 集成遮挡检查
   - 集成云台范围检查
   - 综合返回结果

### 中优先级（后续工作）
4. **与成员 A 确认接口**
   - 阅读反馈
   - 调整接口设计
   - 添加额外功能

5. **开始 P2(1) 双站定位精度**
6. **开始 P3 误差传播分析**

---

## 📊 九、工作量统计

### 今日完成
- ✅ 项目现状检查：1 项
- ✅ 参数核验与标记：1 项（发现待确认问题）
- ✅ 接口文档：1 份（INTERFACE_FOR_A.md，约 200 行）
- ✅ 基础函数实现：2 个（含测试）
- ✅ 测试代码：1 份（test_geometry_basic.py，约 150 行）
- ✅ 算法设计文档：1 份（occlusion_algorithm_design.md，约 300 行）
- ✅ 测试框架：1 份（test_occlusion.py，约 200 行）
- ✅ 日志更新：2 份（progress_log.md, ai_usage_log.md）

### 代码行数
- 新增代码：约 200 行（含注释和文档字符串）
- 新增文档：约 700 行
- 新增测试：约 350 行
- **总计**：约 1250 行

### 测试覆盖
- ✅ 参数测试：15/15 通过
- ✅ 基础几何测试：18/18 通过
- 🔴 遮挡算法测试：待实现

---

## ✅ 十、检查清单

### 第一阶段目标达成情况
- [x] 检查项目现状
- [x] 核验参数可靠性（方位角已按 PDF 明示定义核验）
- [x] 整理供 A 使用的接口（文档已完成）
- [x] 准备基础测试（已完成并通过）
- [x] 说明 A 如何查看接口（在文档中说明）
- [x] 记录日志（已更新）

### 首要目标达成情况
- [x] 成员 A 可以独立推进车辆调度（接口文档已提供）
- [x] 成员 A 不必等待 B 完成全部工作（基础函数可用）
- [x] 接口清晰明确（文档详细）
- [x] 已实现的功能可直接使用（测试通过）

---

## 🎉 结论

### 参数可靠性
- **建筑、车辆、调度中心参数**：✅ 可靠（已通过测试）
- **目标坐标**：按 PDF 第1-2页明示定义与公式计算。

### 可运行函数
- ✅ `calculate_horizontal_distance()` - 完全可用
- ✅ `calculate_elevation_angle()` - 完全可用
- ✅ `is_within_gimbal_range()` - 完全可用

### 未实现函数
- 🔴 `check_building_occlusion()` - P1 核心算法，设计文档已准备
- 🔴 `check_observation_feasibility()` - 综合接口，依赖遮挡算法

### 成员 A 目前可以调用
```python
from shared.constants import *
from shared.geometry_interface import (
    calculate_horizontal_distance,    # ✅ 可用
    calculate_elevation_angle,        # ✅ 可用
    is_within_gimbal_range           # ✅ 可用
)
```

### 下一项需队员自主确定的问题
三维遮挡的判定与边界处理方法；建筑遮挡及综合可观测性仍未实现。

---

**报告生成时间**：2026-11-21
**负责人**：成员 B（江可萌）
**AI 辅助**：Claude Opus 5.5（claude-code CLI）
**报告状态**：第一阶段工程准备完成，遮挡判定待队员研究。
