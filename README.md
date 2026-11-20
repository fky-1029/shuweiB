# ShuWeiCup-B-2026

2026 年数维杯数学建模挑战赛 · B 题：无人机快速定位（Rapid UAV Localization via Coordinated Mobile Vehicles）

## 团队分工

| 成员 | 角色 | 负责模块 |
|---|---|---|
| A | 调度 | P2(2)、P4 |
| B | 几何/误差 | P1、P2(1)、P3 |
| C | 论文/验证 | 论文主文档、图表、结果核查、日志汇总 |

## 目录结构

```
.
├─ problem/          # 赛题与竞赛规则
├─ shared/           # 统一坐标、参数、接口约定
├─ geometry_B/       # B：P1、P2(1)、P3
├─ scheduling_A/     # A：P2(2)、P4
├─ experiments/      # 运行记录、结果表、验证清单
├─ figures/          # 已核对的正式论文图
├─ paper/            # 论文主文件、章节素材
├─ logs/             # 进度/决策/实验/AI 使用台账
└─ requirements.txt  # Python 依赖
```

## 环境与运行

- Python 依赖见 `requirements.txt`，建议在虚拟环境（`.venv/`，已忽略）中安装。
- 统一坐标、参数与接口约定见 `shared/`。

## 进度（按问题）

- [ ] P1 可观测区域与最优站位
- [ ] P2(1) 双站定位精度
- [ ] P2(2) 车辆指派与路径规划
- [ ] P3 误差传播
- [ ] P4 扰动重调度
