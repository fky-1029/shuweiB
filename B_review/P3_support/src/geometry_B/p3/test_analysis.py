"""P3 几何、概率积分和临界根的回归测试（不运行正式蒙特卡洛）。"""
import math

import numpy as np
import pytest

from geometry_B.p3.analysis import (
    LIMIT, R, SIGMA_G, analyze_error_contributions, exact_angle_deviation,
    exact_probability, sigma_position, solve_probability_constraints,
    theoretical_propagation, wrap,
)


def test_zero_and_sign():
    nominal, actual = exact_angle_deviation(0, 0)
    assert nominal == pytest.approx(0, abs=1e-15)
    assert actual == pytest.approx(0, abs=1e-15)
    assert exact_angle_deviation(0, 1)[0] < 0  # 北向估计偏差使正东目标指令向南
    assert exact_angle_deviation(1, 0)[0] == pytest.approx(0)
    assert exact_angle_deviation(0, 0, zero=.1, control=-.04)[1] == pytest.approx(.06)


def test_quadrants_and_wrap():
    for theta in (0, math.pi/2, math.pi, -math.pi/2, 3*math.pi/4):
        n, a = exact_angle_deviation(0, 0, theta=theta)
        assert abs(n) < 1e-14 and abs(a) < 1e-14
    assert wrap(math.pi) == pytest.approx(-math.pi)
    assert wrap(-math.pi) == pytest.approx(-math.pi)
    assert exact_angle_deviation(0, 0, zero=math.pi)[1] == pytest.approx(-math.pi)
    assert exact_angle_deviation(0, 0, zero=math.pi-.01, theta=-math.pi+.01)[1] == pytest.approx(math.pi-.01)
    with pytest.raises(ValueError):
        exact_angle_deviation(R, 0)


def test_variance_invariance():
    p = 2.1
    for theta in np.linspace(-math.pi, math.pi, 13):
        result = theoretical_propagation(p, float(theta))
        assert sum(x*x for x in result["jacobian_rad_per_m"]) == pytest.approx(1/R**2)
        assert result["variance_rad2"] == pytest.approx((p/R)**2+SIGMA_G**2)


def test_non_linearity_and_monotonicity():
    ps = [exact_probability(p) for p in (.3, 1., 2., 4., 8.)]
    assert np.all(np.diff(ps) < 0)
    assert all(0 < p < 1 for p in ps)
    assert abs(exact_probability(3.)-theoretical_propagation(3.)["probability"]) > 1e-5
    assert exact_probability(0) == pytest.approx(2*__import__('scipy').special.ndtr(LIMIT/SIGMA_G)-1)
    assert exact_probability(2., epsabs=1e-11) == pytest.approx(exact_probability(2.), abs=2e-9)


def test_root_and_contributions():
    result = solve_probability_constraints()
    assert result["exact_root_residual"] == pytest.approx(0, abs=1e-9)
    assert abs(result["linear_s_max_m"]-result["exact_s_max_m"]) > 1e-4
    assert exact_probability(sigma_position(result["exact_s_max_m"])) == pytest.approx(.95, abs=1e-9)
    c0 = analyze_error_contributions(sigma_position(0))
    c80 = analyze_error_contributions(sigma_position(80))
    assert sum(c0.values()) == pytest.approx(1.)
    assert c80["position"] > c0["position"]
    assert c80["zero"] < c0["zero"]
