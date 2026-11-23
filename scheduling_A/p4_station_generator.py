import numpy as np
import geometry_interface as geo


def generate_observable_points(target_pos, spacing=0.5):
    """
    生成指定目标的全部可观测网格点。

    target_pos: (x, y, z)
    spacing: 网格间隔，默认0.5m
    """

    x_values = np.arange(0, 100 + spacing / 2, spacing)
    y_values = np.arange(0, 100 + spacing / 2, spacing)

    points = []

    for x in x_values:
        for y in y_values:

            vehicle_pos = (float(x), float(y))

            result = geo.check_observation_feasibility(
                vehicle_pos,
                target_pos
            )

            if result["feasible"]:
                points.append([x, y])

    return np.asarray(points, dtype=float).reshape(-1, 2)
