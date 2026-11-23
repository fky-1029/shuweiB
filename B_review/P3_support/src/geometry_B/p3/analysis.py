"""P3 水平指向误差：各角度内部使用弧度，长度单位 m。运行：python -m geometry_B.p3.analysis。"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import ndtr
from scipy.stats import norm

R = 40.0
LIMIT = math.radians(5)
SIGMA_ZERO = math.radians(0.8)
SIGMA_CONTROL = math.radians(0.6)
SIGMA_G = math.hypot(SIGMA_ZERO, SIGMA_CONTROL)
SEED = 20261122
ROOT = Path(__file__).resolve().parents[2]
COLORS = ("#2a78d6", "#eb6834", "#1baf7a")


def wrap(angle):
    """把弧度角包裹到 [-π,π)，支持数组。"""
    return (np.asarray(angle) + math.pi) % (2 * math.pi) - math.pi


def exact_angle_deviation(delta_x, delta_y, zero=0., control=0., theta=0., radius=R):
    """返回 (名义指令误差, 实际有效指向误差)，弧度。误差 δ=估计位置-真实位置。"""
    if radius <= 0:
        raise ValueError("目标水平距离必须为正")
    dx = radius * math.cos(theta) - np.asarray(delta_x)
    dy = radius * math.sin(theta) - np.asarray(delta_y)
    if np.any((dx == 0) & (dy == 0)):
        raise ValueError("估计位置与目标重合时方位未定义")
    nominal = wrap(np.arctan2(dy, dx) - theta)
    return nominal, wrap(nominal + zero + control)


def sigma_position(s):
    if s < 0:
        raise ValueError("累计行驶距离不能为负")
    return 0.3 + 0.02 * s


def theoretical_propagation(sigma_p, theta=0.):
    """返回雅可比、各项方差 (rad²) 和一阶 ±5° 概率。"""
    if sigma_p < 0:
        raise ValueError("定位标准差不能为负")
    jac = (math.sin(theta) / R, -math.cos(theta) / R)
    parts = ((sigma_p / R)**2, SIGMA_ZERO**2, SIGMA_CONTROL**2)
    variance = sum(parts)
    return {"jacobian_rad_per_m": jac, "variances_rad2": parts,
            "variance_rad2": variance, "probability": 2 * ndtr(LIMIT / math.sqrt(variance)) - 1}


def _angular_density(phi, sigma_p):
    """二维各向同性正态偏移后目标向量的角密度；已解析积去径向变量。"""
    k = R / sigma_p
    cp = math.cos(phi)
    return (math.exp(-k*k/2) / (2*math.pi)
            + k*cp/math.sqrt(2*math.pi)*math.exp(-0.5*(k*math.sin(phi))**2)*ndtr(k*cp))


def _wrapped_acceptance(phi):
    # φ 是相对真实方位的精确名义误差；所有云台误差合并为独立高斯。
    return sum(ndtr((LIMIT-phi+2*math.pi*k)/SIGMA_G)
               - ndtr((-LIMIT-phi+2*math.pi*k)/SIGMA_G) for k in (-1, 0, 1))


def exact_probability(sigma_p, *, epsabs=2e-10):
    """确定性一维角积分；极角密度解析积分径向，积分绝对误差约 epsabs。"""
    if sigma_p < 0:
        raise ValueError("定位标准差不能为负")
    if sigma_p == 0:
        return 2*ndtr(LIMIT/SIGMA_G)-1
    # 角密度关于 0 对称；在阈值附近分段以适应窄峰。
    cuts = [0., LIMIT/2, LIMIT, 2*LIMIT, math.pi/2, math.pi]
    value = 0.
    for lo, hi in zip(cuts[:-1], cuts[1:]):
        piece, error = quad(lambda phi: _angular_density(phi, sigma_p)
                            * _wrapped_acceptance(phi), lo, hi,
                            epsabs=epsabs/12, epsrel=1e-11, limit=200)
        value += piece
    return 2*value


def solve_probability_constraints():
    """求一阶/精确标准差上界；80m 可行域 a+80b≤精确上界。"""
    z = norm.ppf(0.975)
    inside = (LIMIT/z)**2 - SIGMA_G**2
    if inside <= 0:
        raise ValueError("即使定位无误，云台误差也不能满足阈值")
    linear_sigma = R*math.sqrt(inside)
    if linear_sigma < sigma_position(0):
        raise ValueError("s=0 已不满足一阶阈值")
    # σ 增大时检测单调性，防止未经核查即把局部根认作最大允许距离。
    grid = np.linspace(0, R, 81)
    values = [exact_probability(float(x)) for x in grid]
    if any(b > a + 1e-8 for a, b in zip(values, values[1:])):
        raise ArithmeticError("概率随定位标准差不单调，需重新审查可行集合")
    if values[0] < 0.95 or values[-1] >= 0.95:
        raise ArithmeticError("精确模型无有效求根区间")
    exact_sigma = brentq(lambda p: exact_probability(p)-0.95, 0, R, xtol=1e-10)
    if exact_sigma < sigma_position(0):
        raise ValueError("精确模型 s=0 不满足约束")
    return {"z_975": float(z), "linear_sigma_bound_m": linear_sigma,
            "exact_sigma_bound_m": exact_sigma,
            "linear_s_max_m": (linear_sigma-0.3)/0.02,
            "exact_s_max_m": (exact_sigma-0.3)/0.02,
            "linear_a_plus_80b_bound_m": linear_sigma,
            "exact_a_plus_80b_bound_m": exact_sigma,
            "exact_root_residual": exact_probability(exact_sigma)-0.95}


def analyze_error_contributions(sigma_p):
    """一阶方差份额：定位、云台零偏、云台控制误差。"""
    var = theoretical_propagation(sigma_p)["variances_rad2"]
    return dict(zip(("position", "zero", "control"), (v/sum(var) for v in var)))


def monte_carlo(sigma_p, n, seed, theta=0.):
    """三个物理来源独立采样（定位来源含 x/y 两个独立坐标）；Wilson 95% CI。"""
    if sigma_p < 0 or n <= 0:
        raise ValueError("定位标准差及样本数不合法")
    rng = np.random.default_rng(seed)
    success = 0
    linear_success = 0
    # 分块避免大量峰值内存；随机流次序固定，记录种子即可复现。
    for size in [100_000]*(n//100_000) + ([n%100_000] if n%100_000 else []):
        dx = rng.normal(0, sigma_p, size)
        dy = rng.normal(0, sigma_p, size)
        zero = rng.normal(0, SIGMA_ZERO, size)
        control = rng.normal(0, SIGMA_CONTROL, size)
        nominal, actual = exact_angle_deviation(dx, dy, zero, control, theta)
        success += int(np.count_nonzero(np.abs(actual) <= LIMIT))
        linear = (math.sin(theta)*dx-math.cos(theta)*dy)/R+zero+control
        linear_success += int(np.count_nonzero(np.abs(linear) <= LIMIT))
    p = success/n
    z = norm.ppf(0.975)
    center = (p+z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return {"seed": seed, "n": n, "success": success, "probability": p,
            "wilson_95": (center-half, center+half),
            "linear_empirical_probability": linear_success/n}


def compare_theory_simulation(sigma_p, n, seed, theta=0.):
    return {"sigma_p_m": sigma_p,
            "linear_probability": theoretical_propagation(sigma_p)["probability"],
            "exact_probability": exact_probability(sigma_p),
            "simulation": monte_carlo(sigma_p, n, seed, theta)}


def export_results_and_figures(output_dir=None, *, quick=False):
    """仅输出新的 P3 文件；--quick 小样本调试，默认独立百万样本临界核查。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from geometry_B.figure_style import apply_figure_style

    apply_figure_style()
    out = Path(output_dir) if output_dir else ROOT / "figures" / "p3_output"
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"输出目录非空，拒绝覆盖已有结果：{out}")
    out.mkdir(parents=True, exist_ok=True)
    results = solve_probability_constraints()
    linear_s, exact_s = results["linear_s_max_m"], results["exact_s_max_m"]
    # 独立随机流，不共用同一批样本来伪装重复试验。
    scenarios = [("s=0", sigma_position(0), 100_000),
                 ("s=linear boundary", results["linear_sigma_bound_m"], 1_000_000),
                 ("s=exact boundary", results["exact_sigma_bound_m"], 1_000_000),
                 ("s=exact boundary repeat", results["exact_sigma_bound_m"], 1_000_000),
                 ("s=80", sigma_position(80), 100_000),
                 ("a=bound,b=0", results["exact_sigma_bound_m"], 100_000),
                 ("a=0,b=bound/80", results["exact_sigma_bound_m"], 100_000)]
    if quick:
        scenarios = [(label, sigma, 20_000) for label, sigma, _ in scenarios]
    results["scenarios"] = {label: compare_theory_simulation(sigma, n, SEED+i)
                             for i, (label, sigma, n) in enumerate(scenarios)}
    results["contributions"] = {label: analyze_error_contributions(sigma_position(s))
                                for label, s in (("s=0", 0), ("s=linear boundary", linear_s),
                                                 ("s=exact boundary", exact_s), ("s=80", 80))}
    results["model_convention"] = ("nominal=atan2(target-estimated)-atan2(target-true); "
                                    "effective=wrap(nominal+zero_offset+control_error)")
    results["seed"] = SEED
    results["quick"] = quick
    results["versions"] = {"numpy": np.__version__}
    import scipy
    results["versions"]["scipy"] = scipy.__version__

    s_grid = np.linspace(0, max(80, exact_s*1.35), 85)
    lp = np.array([theoretical_propagation(sigma_position(s))["probability"] for s in s_grid])
    ep = np.array([exact_probability(sigma_position(s)) for s in s_grid])
    fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
    ax.plot(s_grid, lp, color=COLORS[0], label="First-order normal", lw=2)
    ax.plot(s_grid, ep, color=COLORS[1], ls="--", label="Exact angle integral", lw=2)
    ax.axhline(.95, color="#444444", ls=":", label="Requirement: 95%")
    ax.axvline(exact_s, color="#777777", lw=1, ls="-.", label="Exact boundary")
    ax.set(xlabel="Cumulative travel distance s (m)", ylabel="P(|effective bearing error| ≤ 5°)",
           ylim=(max(0, min(ep.min(),lp.min())-0.025), 1.005))
    ax.legend(loc="best")
    fig.savefig(out / "p3_probability_vs_distance.png", dpi=220)
    plt.close(fig)

    bound = results["exact_sigma_bound_m"]
    b = np.linspace(0, bound/80, 200)
    fig, ax = plt.subplots(figsize=(6, 4.5), layout="constrained")
    ax.fill_between(b, 0, bound-80*b, color=COLORS[0], alpha=.22, label="Exact-model feasible")
    ax.plot(b, bound-80*b, color=COLORS[0], lw=2, label="a + 80b = exact bound")
    ax.plot(b, results["linear_sigma_bound_m"]-80*b, color=COLORS[1], ls="--",
            lw=1.8, label="First-order boundary")
    ax.set(xlabel="Growth coefficient b (m/m)", ylabel="Initial position SD a (m)",
           xlim=(0, bound/80*1.06), ylim=(0, bound*1.07))
    ax.legend(loc="best")
    fig.savefig(out / "p3_parameter_feasible_region.png", dpi=220)
    plt.close(fig)

    labels = ["s=0", "s=linear boundary", "s=80"]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
    bottom = np.zeros(3)
    for key, name, color, hatch in zip(("position", "zero", "control"),
                                       ("Vehicle position", "Gimbal zero offset", "Gimbal control"),
                                       COLORS, ("", "//", "\\\\")):
        heights = np.array([results["contributions"][label][key]*100 for label in labels])
        ax.bar(x, heights, bottom=bottom, width=.62, label=name, color=color,
               hatch=hatch, edgecolor="white", linewidth=1)
        bottom += heights
    ax.set(xticks=x, xticklabels=["0 m", f"{linear_s:.2f} m (linear limit)", "80 m"],
           ylabel="Share of first-order angular variance (%)", ylim=(0, 105))
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.13), ncol=3, frameon=False)
    fig.savefig(out / "p3_variance_contributions.png", dpi=220)
    plt.close(fig)

    path = out / "p3_analysis_results.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="用小样本调试；输出目录须为空")
    parser.add_argument("--output-dir", type=Path, help="输出目录（默认 figures/p3_output/；须为空）")
    args = parser.parse_args()
    print(json.dumps(export_results_and_figures(args.output_dir, quick=args.quick),
                     ensure_ascii=False, indent=2))
