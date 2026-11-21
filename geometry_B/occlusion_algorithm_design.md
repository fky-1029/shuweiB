# P1 建筑遮挡算法设计文档

## 📋 问题定义

**核心问题**：判断从车辆摄像头到目标的视线是否被建筑物遮挡。

### 输入
- 摄像头位置：`(x_cam, y_cam, z_cam)` = `(x_vehicle, y_vehicle, CAMERA_HEIGHT)`
- 目标位置：`(x_target, y_target, z_target)`
- 建筑物列表：每栋建筑为轴对齐包围盒（AABB）
  - 平面范围：`[x_min, x_max] × [y_min, y_max]`
  - 高度范围：`[0, height]`

### 输出
- `(is_occluded: bool, building_id: Optional[int])`
- 若被遮挡，返回第一个遮挡的建筑ID

---

## 🔍 算法选项

### 方案 1：射线-AABB 相交检测（推荐）

**原理**：
- 将视线建模为三维射线：`P(t) = P_cam + t * (P_target - P_cam)`，其中 `t ∈ [0, 1]`
- 检测射线与每栋建筑的 AABB 是否相交
- 使用 Slab 方法（逐维度检查）

**优点**：
- 标准算法，成熟稳定
- 高效（每栋建筑仅需常数时间）
- 易于实现和调试

**伪代码**：
```python
def ray_aabb_intersection(ray_origin, ray_direction, aabb):
    # Slab 方法：对每个轴计算进入和离开时间
    t_min = -inf
    t_max = +inf

    for axis in [x, y, z]:
        if ray_direction[axis] != 0:
            t1 = (aabb_min[axis] - ray_origin[axis]) / ray_direction[axis]
            t2 = (aabb_max[axis] - ray_origin[axis]) / ray_direction[axis]

            t_min = max(t_min, min(t1, t2))
            t_max = min(t_max, max(t1, t2))
        else:
            # 射线平行于该轴
            if ray_origin[axis] < aabb_min[axis] or ray_origin[axis] > aabb_max[axis]:
                return False  # 不相交

    # 检查相交区间是否有效
    if t_min > t_max or t_max < 0:
        return False

    # 检查相交点是否在视线段内（0 <= t <= 1）
    return t_min <= 1 and t_max >= 0
```

**参考资源**：
- [Ray-AABB Intersection (Scratchapixel)](https://www.scratchapixel.com/lessons/3d-basic-rendering/minimal-ray-tracer-rendering-simple-shapes/ray-box-intersection)
- [Slab Method Explanation](https://education.siggraph.org/static/HyperGraph/raytrace/rtinter3.htm)

---

### 方案 2：参数方程求交

**原理**：
- 射线参数方程：`P(t) = P_cam + t * D`，其中 `D = P_target - P_cam`
- 检查射线与建筑物 6 个面的相交
- 计算所有相交点，判断是否在建筑物内

**优点**：
- 直观易懂
- 适合教学和论文说明

**缺点**：
- 需要检查 6 个面，代码较长
- 容易出现边界情况遗漏

---

### 方案 3：分段检查法

**原理**：
- 在视线上采样多个点
- 检查每个点是否在建筑物内部

**优点**：
- 实现简单

**缺点**：
- 精度依赖采样密度
- 可能遗漏薄建筑物
- 效率低（需要大量采样）

**不推荐**：精度不可靠，不适合竞赛

---

## ✅ 推荐方案：射线-AABB 相交检测

### 实现步骤

1. **计算射线参数**
   ```python
   ray_origin = (x_cam, y_cam, z_cam)
   ray_direction = (x_target - x_cam, y_target - y_cam, z_target - z_cam)
   ```

2. **遍历所有建筑物**
   ```python
   for building in buildings:
       aabb = {
           'x_min': building['x_min'], 'x_max': building['x_max'],
           'y_min': building['y_min'], 'y_max': building['y_max'],
           'z_min': 0.0, 'z_max': building['height']
       }

       if ray_aabb_intersect(ray_origin, ray_direction, aabb):
           return (True, building['id'])
   ```

3. **Slab 方法实现**
   - 对 x、y、z 三个轴分别计算进入/离开时间
   - 取交集判断是否有效相交
   - 检查相交点是否在视线段 `[0, 1]` 内

---

## 🧪 测试用例设计

### 基础测试
1. ✓ **无遮挡**：视线完全避开所有建筑
2. ✓ **完全遮挡**：视线穿过建筑物中心
3. ✓ **边界情况**：视线擦过建筑物边缘
4. ✓ **建筑背后**：目标在建筑后面，但视线不经过建筑
5. ✓ **多栋建筑**：视线可能被多栋建筑遮挡

### 边界测试
6. ✓ **视线平行于地面**：`z_cam == z_target`
7. ✓ **垂直视线**：摄像头正上方或正下方
8. ✓ **视线经过建筑顶点**：精确经过 8 个顶点之一
9. ✓ **视线经过建筑边**：精确沿着建筑物棱边
10. ✓ **射线方向分量为 0**：平行于某个轴

### 实际场景测试
11. ✓ **车辆1 → 目标1**：根据实际参数检查
12. ✓ **车辆2 → 目标2**：根据实际参数检查
13. ✓ **所有车辆-目标组合**：15 种组合的遮挡情况

---

## 🚧 待人工决定的问题

### Q1: 边界情况处理
**问题**：视线恰好擦过建筑物边缘或顶点时，是否算遮挡？

**选项**：
- A. 算遮挡（保守策略）
- B. 不算遮挡（激进策略）
- C. 按物理意义：只要有一点接触就算遮挡

**建议**：选择 A（保守策略），避免低估遮挡风险

---

### Q2: 浮点数精度
**问题**：判断相交时的浮点数容差？

**当前建议**：
- 使用 `epsilon = 1e-9` 作为容差
- 避免因浮点误差导致的错误判断

---

### Q3: 多建筑遮挡
**问题**：视线穿过多栋建筑时，返回哪一个？

**选项**：
- A. 返回第一个遮挡的建筑（最接近摄像头）
- B. 返回所有遮挡的建筑列表
- C. 只返回是否被遮挡（不区分建筑）

**建议**：选择 A，返回最近的遮挡建筑

---

## 📚 参考资料

### 推荐阅读
1. [Scratchapixel - Ray-Box Intersection](https://www.scratchapixel.com/lessons/3d-basic-rendering/minimal-ray-tracer-rendering-simple-shapes/ray-box-intersection)
2. [Real-Time Rendering, 4th Edition - Chapter 22.7](http://www.realtimerendering.com/)
3. [PBRT Book - Ray-Bounds Intersections](https://www.pbr-book.org/)

### 相关算法
- Möller-Trumbore 算法（三角形相交）
- BVH 加速结构（大量建筑物场景）
- 空间分割（Octree、KD-Tree）

---

## 🔄 实现流程

### 第一步：理解算法原理
- [ ] 阅读推荐资料（Scratchapixel 教程）
- [ ] 手工推导 1-2 个简单例子
- [ ] 绘制示意图理解几何关系

### 第二步：实现核心函数
- [ ] 实现 `ray_aabb_intersect()` 函数
- [ ] 处理射线方向分量为 0 的特殊情况
- [ ] 处理浮点数精度问题

### 第三步：集成到接口
- [ ] 实现 `check_building_occlusion()`
- [ ] 遍历所有建筑物
- [ ] 返回第一个遮挡的建筑ID

### 第四步：测试验证
- [ ] 编写单元测试（基础测试 + 边界测试）
- [ ] 可视化测试结果（可选）
- [ ] 验证实际场景数据

---

## ⚠️ 重要提醒

1. **这是 P1 的核心算法，必须由队员自主设计和实现**
2. **不要直接复制粘贴代码**，理解原理后自己编写
3. **建议使用 ChatGPT/Claude 讨论数学原理，但不要直接要求实现代码**
4. **实现后必须充分测试**，包括边界情况和实际场景
5. **建议先在纸上画图，理解几何关系后再编码**

---

## 📝 进度跟踪

- [ ] 算法方案确定
- [ ] 边界情况处理策略确定
- [ ] 核心函数实现
- [ ] 单元测试编写
- [ ] 基础测试通过
- [ ] 边界测试通过
- [ ] 实际场景验证
- [ ] 代码审查与优化

---

**文档创建日期**：2026-11-21
**负责人**：成员 B（江可萌）
**状态**：设计阶段，待实现
