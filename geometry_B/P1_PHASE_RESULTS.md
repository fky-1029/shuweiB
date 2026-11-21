# P1 阶段成果（T1 可观测区域）

本阶段按以下三个约束的**交集**判定车辆停车位置：

1. 半径 `1.5 m` 的车辆圆盘完整位于 `100 m × 100 m` 场地内，且不侵入五栋建筑的水平投影；恰好接触允许。
2. 摄像头（离地 `2 m`）到目标的有限三维视线线段不与建筑长方体相交；与面、棱、顶点接触均计为遮挡。
3. 云台仰角处于闭区间 `[-10°, 80°]`。

按 `0.5 m` 间距采样场地坐标，共 `201 × 201 = 40401` 个网格点，其中 `22788` 个满足三项约束。**有效网格点数量不是连续区域面积**，图像仅表示本次采样结果。尚未求得最优站位，也未验证连续区域边界及优化精度。

- `figures/p1_t1_observable_region_0p5m.png`：实际网格计算结果与五栋建筑、T1 水平投影叠加，可供 C 撰写论文时核对并使用。
- `figures/p1_t1_observable_points_0p5m.csv`：有效采样点的东向 `x`、北向 `y` 坐标，供后续计算与复核。
- `figures/p1_t1_observable_grid_0p5m.npz`：`x_values`、`y_values`、`observable` 布尔矩阵及采样参数，`observable[j,i]` 对应 `(x_values[i], y_values[j])`，供后续计算与验证。

从项目根目录运行 `.venv/bin/python -m geometry_B.generate_region` 可重新生成；测试命令为 `python3 -m unittest discover -s geometry_B -v`。调度模块调用方式见 `shared/INTERFACE_FOR_A.md`；接口不负责行驶路径或调度。
