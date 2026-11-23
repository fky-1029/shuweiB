# P3 支撑材料

## 内容与来源

源代码快照来自 `geometry_B/p3/analysis.py`、`test_analysis.py`；输出 JSON 来自项目实际存在的 `figures/p3_verified_20261122/p3_analysis_results.json`。注意项目还存在 `figures/p3_validation_20261122/` 旧版结果，不应与 verified 版本混用。此包是审查快照，不是含完整 Git 历史的仓库。

核心常数：目标水平距离 `R=40 m`，成功界限 `|e|≤5°`，定位坐标误差各轴标准差 `σp(s)=0.3+0.02s m`，云台零偏 `0.8°`、控制误差 `0.6°`，均按代码的独立随机误差假设。代码弧度内部计算，一阶角误差含定位雅可比项 `(sinθ·dx−cosθ·dy)/R`，并合成两个云台误差。精确概率通过对定位角与包裹云台高斯误差积分计算；临界位置标准差由数值求根确定，Monte Carlo 只作交叉验证。

Verified JSON：精确临界距离 `66.83725842777815 m`，一阶临界距离 `66.9222992390813 m`；精确 `σp` 上限 `1.6367451685555632 m`，一阶上限 `1.638445984781626 m`。所以 `66.84 m` 只是四舍五入展示，不能直接用作严格执行上限；80 m 情形的精确充分条件为 `a+80b≤1.6367451686 m`，论文 `1.6367 m` 是向下截断的保守值。方差贡献是线性一阶方差分解，不是非线性尾概率归因。

## 复核命令

从原项目根目录，只读测试：

```bash
.venv/bin/python -m pytest -p no:cacheprovider geometry_B/p3/test_analysis.py -q
```

或在已安装 pytest 的环境中运行 `python -m unittest` 并导入 pytest 测试模块（更推荐 pytest 命令）。计算/完整 Monte Carlo 运行会生成结果，应使用新输出目录：

```bash
.venv/bin/python -m geometry_B.p3.analysis --output-dir /tmp/p3-reproduction-new
```

依赖 NumPy、SciPy；出图另需 Matplotlib。结果 JSON 包括种子、样本数、成功数及 Wilson 区间。仅复制 JSON 不能独立证明它由某个源码哈希生成，因此版本复核应配合源码与运行记录。
