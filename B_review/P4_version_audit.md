# P4 版本与结果来源审查

- 审查对象：GitHub 远端 `origin/陈依` 分支
- 核查时间：2026-11-24
- 远端提交：`d9c908b853a6825e0e539b4c77b8f4ef159bccc1`（2026-11-23 13:44:14 +0800，`Add files via upload`）
- 审查范围：远端 Git tree、P4/P2 源码、已提交的图像和项目内可见运行记录
- 限制：未读取或修改其他审查者的材料；未运行生成结果的代码；未修改源代码、论文或结果文件。本文件本身是用户明确要求写入的审查记录。

## 一、结论摘要

在 `陈依` 分支最新提交中，确认上传了：

1. P4 入口和策略源码；
2. 一个 P2(2) 排班穷举源码；
3. 若干调度甘特图 PNG；
4. `shared/observable_points.json`。

但没有找到：

- 超出 S0–S7 的额外场景入口或参数表；
- `S8` 及之后的场景定义；
- 对应的额外场景运行日志；
- P4 逐场景 CSV/JSON；
- 能把某次结果绑定到源码提交、依赖版本和运行命令的执行记录。

因此当前可审计结论是：**陈依分支的 P4 实现明确是 S0–S7 八个代表场景。**此前把“24”写入审查目标是审查表述错误，不是项目代码或论文中的场景数量。`11.0234 s` 有下游手写基准表和 P2(2) 穷举器源码的间接支持，但没有该穷举器实际运行输出，因此“该值由该版本求解器实际产生并已证明全局最优”仍为**未验证**。

## 二、远端文件清单

### 2.1 P4 入口和依赖

远端 `d9c908b` 中的相关文件：

```text
scheduling_A/main_experiments.py
scheduling_A/p4_keep_original_policy.py
scheduling_A/p4_reschedule_policy.py
scheduling_A/p4_station_generator.py
scheduling_A/p4_vehicle_state.py
scheduling_A/timeline_printer.py
shared/observable_points.json
shared/constants.md
```

P4 入口还导入：

```python
import path_planning as path_plan
import geometry_interface as geo
import constants as const
```

位置：`scheduling_A/main_experiments.py:29-35`。

但是远端 tree 中未找到与这些导入名对应的完整 `scheduling_A/path_planning.py`、`scheduling_A/geometry_interface.py`、`scheduling_A/constants.py`。同时，`scheduling_A/p4_reschedule_policy.py:615` 使用：

```python
P4_DIRECTORY / "observable_points.json"
```

即期待 `scheduling_A/observable_points.json`，但远端 tree 中看到的是 `shared/observable_points.json`。因此仅凭远端提交树，无法确认 `scheduling_A/main_experiments.py` 可在干净 checkout 中直接运行。

### 2.2 P4 场景入口

`Scheduling_A/main_experiments.py:4-5` 的模块说明写明：

```text
P4 全场景实验入口：
对比“保留原计划策略”与“动态重调度策略”在 S0-S7 下的表现。
```

`main_experiments.py:101-110` 定义的场景为：

| 场景 | 参数覆盖 |
|---|---|
| S0 | 无扰动 |
| S1 | 新警报 |
| S2 | 单车辆故障 |
| S3 | 通信中断 |
| S4 | 新警报 + 车辆故障 |
| S5 | 新警报 + 通信中断 |
| S6 | 车辆故障 + 通信中断 |
| S7 | 新警报 + 车辆故障 + 通信中断 |

没有 `S8`–`S23`，也没有长度为 24 的场景数组或场景参数文件。

**结论：**八场景存在，有源码证据；没有发现超出 S0–S7 的额外场景，项目当前场景数量就是 8。此前把“24”列为核验目标属于本审查文案错误，应删除，不应理解为项目声称有 24 个场景。

## 三、P4 参数和题目规则核对

### 3.1 新警报 T4

`main_experiments.py:93-99` 固定：

```python
azimuth = 120.0
horizontal_distance = 40.0
altitude = 50.0
arrival_time = 5.0
```

因此当前入口只运行一个 T4：

```text
θ=120°，R=40 m，H=50 m，t=5 s
```

`p4_reschedule_policy.py:638-661` 能根据给定 θ、R 动态生成 T4 的可观测点并保存 CSV，但入口没有循环多个 θ/R，也没有随机种子、分层采样或代表性坐标表。

**结论：**动态生成函数存在；“随机生成多组代表性 T4 坐标并完成实验”未实现、未验证。不能把单个固定点外推为参数鲁棒性结论。

### 3.2 5 s 扰动和通信恢复

代码中的新警报到达时刻固定为 `5.0`。通信恢复时间在八场景中使用 `15.0`，故障车辆固定为 `V2`，见 `main_experiments.py:101-110`。

这覆盖了扰动类型的组合，但没有覆盖：

- 多个故障车辆；
- 多个恢复时间；
- 多个 T4 方位/距离；
- 额外的参数化场景实验。

题目约束要求：扰动发生于 5 s；已开始的观测不能重排；未开始的任务可重新分配；故障车退出；通信中断期间沿用已下发命令且不能接收新命令；恢复后方可重调度；评价窗口为 `[0,60] s`。

远端源码中能看到这些机制的意图，但没有一次已保存的完整运行日志逐条证明每个场景都按上述规则执行。尤其需要注意：源码是否把“已下发但未开始”和“尚未下发”严格区分，不能仅由场景汇总图确认。

## 四、P2(2) 新增穷举器与 11.0234 s

### 4.1 新增求解器

远端新增：

```text
scheduling_A/p2_2_optimal_scheduler.py
```

关键位置：

- `:230-257`：`generate_all_plans()`；
- `:236-249`：枚举 5 辆车、3 个目标、每个目标两辆车的任务分配及顺序；
- `:459-508`：生成全部方案、逐个评价、选取最小 makespan，并输出甘特图。

源码中确实有：

```python
all_plans = generate_all_plans()
for plan in all_plans:
    ...
```

所以相较于此前版本，已经有“穷举排班方案”的源码证据。

### 4.2 仍缺少运行来源链

远端没有找到该脚本的：

- 命令行记录；
- stdout/stderr 日志；
- 机器可读的最优方案 JSON/CSV；
- 运行时间；
- 源码和依赖版本快照；
- 生成的 `11.0234` 原始精度输出。

远端 `scheduling_A/p4_vehicle_state.py:48-126` 中的 `BASELINE_PLAN` 仍是手写时间表。例如：

- `V2` 的 `observe_start = 11.0234`（`:63-73`）；
- `V5` 后续 T3 任务也使用 `11.0234`（`:117-126`）。

这证明 P4 后续代码**读取并沿用了**这个常量，不证明该常量由远端新增的穷举器实际生成。

因此应区分：

| 主张 | 结论 |
|---|---|
| 远端有 P2(2) 穷举器源码 | 可证实 |
| 穷举器理论上枚举排班方案 | 可由源码证实 |
| 穷举器实际运行过 | 未验证 |
| 11.0234 s 是该次运行的输出 | 未验证 |
| 11.0234 s 已由完整结果文件复核 | 未验证 |
| 11.0234 s 是全局最优 | 未验证 |
| 13.11 s 和 15.91% 改善率由该运行独立得到 | 未验证 |

远端已有的 PNG：

```text
scheduling_A/Execution Result of Global Scheduling Algorithm.png
scheduling_A/Execution Result of Nearest Assignment Heuristic.png
scheduling_A/Schedule_Timeline_Output（1）.png
scheduling_A/Schedule_Timeline_Output（2）.png
scheduling_A/Schedule_Timeline_Output（3）.png
scheduling_A/schedule_gantt.png
```

这些是图像级证据，不能提供上述缺失的运行来源链。

## 五、Git 提交和版本结论

远端最新提交历史中与该版本直接相关的是：

```text
d9c908b  2026-11-23 13:44:14 +0800  Add files via upload
432edbe  2026-11-23 02:07:38 +0800  Add files via upload
8411a70  2026-11-22 23:04:57 +0800  Add files via upload
b0e4686  2026-11-22 16:30:22 +0800  Add files via upload
c9df5c0  2026-11-22 16:28:20 +0800  Add files via upload
```

`d9c908b` 上传了 P4 入口、策略和状态文件；此前提交包含排班器、共享可观测点和图像。没有提交显示为“24 场景运行结果”或包含场景结果 CSV/JSON。

因此版本线应写成：

```text
远端陈依分支 d9c908b
  ├─ scheduling_A/main_experiments.py：S0-S7 八场景入口
  ├─ scheduling_A/p4_*.py：P4 策略实现
  ├─ scheduling_A/p2_2_optimal_scheduler.py：P2(2) 穷举器源码
  ├─ scheduling_A/p4_vehicle_state.py：手写 BASELINE_PLAN，含 11.0234
  └─ PNG：图像产物，无可核验运行日志
```

不能建立：

```text
11.0234 或 Table 7 数字
  → 某次实际命令
  → d9c908b 的完整源码及依赖
  → 可复核 CSV/JSON
```

## 六、最终审查结论

1. **陈依分支当前 P4 入口是八个场景 S0–S7。**此前出现“24 场景”是本审查表述错误，已更正；项目当前没有 24 场景主张。
2. **新增了 P2(2) 穷举调度器源码。**这改善了“存在求解方法”的证据，但不等于已有运行结果来源证据。
3. **11.0234 s 仍不能独立认证为该穷举器输出的全局最优值。**它目前主要以手写 `BASELINE_PLAN` 常量和论文/PNG 间接存在。
4. **T4 仍只有固定 `(θ,R,H)=(120°,40 m,50 m)`。**没有发现随机代表点实验。
5. **远端 tree 还不构成干净可运行的 P4 快照。**入口所需的一些模块和 `scheduling_A/observable_points.json` 未在该目录树中出现。
6. 若要补强“未验证”项，应补交：运行命令、完整 stdout、S0–S7 场景参数表、逐场景 JSON/CSV、入口及依赖文件哈希、输入数据哈希和生成时间。不存在所谓 24 场景的待补交项。

## 七、本次只读核查命令

实际执行的命令类型包括：

```bash
git fetch origin '陈依'
git log --format='%h %ci %s' -10 FETCH_HEAD
git ls-tree -r --name-only FETCH_HEAD
git grep -n -E 'SCENARIOS|S[0-9]+|24|scenario|场景|T4|random|seed' FETCH_HEAD -- 'scheduling_A/*' 'shared/*'
git show FETCH_HEAD:<path>
git diff FETCH_HEAD~1 FETCH_HEAD --stat
```

未执行 P4/P2 生成脚本，未重新生成任何图表、CSV 或 JSON。
