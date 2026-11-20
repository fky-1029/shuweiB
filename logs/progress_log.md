# 进度日志 progress_log.md

> 每次重要进展追加一条，格式如下（示例字段，内容留空待填）。

## 日期/时间：2024-11-20 23:30-00:30
- 负责人：B（江可萌）
- 涉及问题：准备阶段 - 环境配置、参数定义、接口框架
- 本次完成：
  1. ✅ Python 环境配置（Python 3.14.4 + 虚拟环境 + NumPy/Matplotlib/SciPy）
  2. ✅ 创建 shared/constants.py（统一参数定义）
  3. ✅ 创建 shared/geometry_interface.py（几何接口框架）
  4. ✅ 创建 shared/test_environment.py（环境测试）
  5. ✅ 紧急参数纠错（建筑、车辆、目标参数全部错误，已修正）
  6. ✅ 创建 shared/test_parameters.py（参数一致性测试）
  7. ✅ 修正目标坐标转换公式
  8. ✅ 所有测试通过
- 对应 Issue / Commit / PR：无（未提交）
- 遗留问题：
  1. ⚠️ **待人工确认**：方位角定义（PDF 未明确起始方向和旋转方向）
  2. geometry_interface.py 中 4 个核心函数仅为占位（NotImplementedError）
  3. 尚未开始 P1、P2(1)、P3 的核心建模
- 下一步与交接对象：
  1. 人工确认方位角定义
  2. 开始实现基础几何函数（距离、仰角计算）
  3. 设计 P1 建筑遮挡算法
  4. 与成员 A 确认接口是否满足调度需求

---

## 日期/时间：YYYY-MM-DD HH:MM
- 负责人：A / B / C
- 涉及问题：P1 / P2(1) / P2(2) / P3 / P4
- 本次完成：
- 对应 Issue / Commit / PR：
- 遗留问题：
- 下一步与交接对象：

---
