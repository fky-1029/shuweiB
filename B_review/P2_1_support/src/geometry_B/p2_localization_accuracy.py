"""双站水平测向交会的一阶定位精度；不负责站位合法性、路径或搜索。"""
from __future__ import annotations

import math

from geometry_B.p2_two_station_tools import distance_2d

# 无量纲 |sin(gamma)| 阈值，只用于浮点近共线判定；不是物理精度门槛。
# 1e-12 对应靠近 0°/180° 约 5.73e-11°。实际应用还须检查
# sigma_rad / |sin(gamma)| 是否足够小，以确保一阶线性化有效。
DEGENERATE_SIN_THRESHOLD = 1e-12


def _point(point: tuple[float, float], name: str) -> tuple[float, float]:
    try:
        x, y = point
        x, y = float(x), float(y)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是二维有限坐标（米）") from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError(f"{name} 必须是二维有限坐标（米）")
    return x, y


def calculate_localization_metrics(
    station1: tuple[float, float],
    station2: tuple[float, float],
    target: tuple[float, float],
    sigma_deg: float = 1.0,
) -> dict:
    """计算两站测向的一阶水平位置 RMSE（米）。

    方位角自正东逆时针计，在 [0,360)°；交会角是目标处两站射线夹角，
    在 [0,180]°。若 |sin(gamma)| <= 1e-12，则退化并返回无限 RMSE。
    站点与目标重合时方位未定义，抛 ValueError，而不是伪造精度。
    输入坐标与输出距离、RMSE 单位均为米。
    """
    x1, y1 = _point(station1, "station1")
    x2, y2 = _point(station2, "station2")
    xt, yt = _point(target, "target")
    try:
        sigma_deg = float(sigma_deg)
    except (TypeError, ValueError) as exc:
        raise ValueError("sigma_deg 必须为正的有限角度（度）") from exc
    if not math.isfinite(sigma_deg) or sigma_deg <= 0:
        raise ValueError("sigma_deg 必须为正的有限角度（度）")

    dx1, dy1 = xt - x1, yt - y1
    dx2, dy2 = xt - x2, yt - y2
    r1 = math.hypot(dx1, dy1)
    r2 = math.hypot(dx2, dy2)
    if r1 == 0 or r2 == 0:
        raise ValueError("站位与目标水平投影重合：测向方位角未定义")
    if not all(math.isfinite(v) for v in (dx1, dy1, dx2, dy2, r1, r2)):
        raise ValueError("坐标差或距离超出浮点可表示范围")
    baseline = distance_2d((x1, y1), (x2, y2))
    if not math.isfinite(baseline):
        raise ValueError("基线超出浮点可表示范围")
    alpha1 = math.degrees(math.atan2(dy1, dx1)) % 360.0
    alpha2 = math.degrees(math.atan2(dy2, dx2)) % 360.0

    # 先单位化再叉积，避免 r1*r2 溢出并降低尺度敏感性。
    u1x, u1y = dx1 / r1, dy1 / r1
    u2x, u2y = dx2 / r2, dy2 / r2
    signed_sine = u1x * u2y - u1y * u2x
    cosine = u1x * u2x + u1y * u2y
    sine = min(1.0, abs(signed_sine))
    gamma = math.degrees(math.atan2(sine, cosine))
    degenerate = sine <= DEGENERATE_SIN_THRESHOLD
    sigma_rad = math.radians(sigma_deg)
    rmse = math.inf if degenerate else sigma_rad * math.hypot(r1, r2) / sine

    return {
        "r1_m": r1,
        "r2_m": r2,
        "baseline_m": baseline,
        "alpha1_deg": alpha1,
        "alpha2_deg": alpha2,
        "gamma_deg": gamma,
        "rmse_m": rmse,
        "degenerate": degenerate,
    }
