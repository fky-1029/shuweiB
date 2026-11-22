"""Export paper figures from audited P1/P2/P3 result files only.

This module does not run optimization, Monte Carlo, or alter any numerical result.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from geometry_B.figure_style import COLORS, apply_figure_style
from geometry_B.observable_region_plot import plot_field
from shared.constants import BUILDINGS, FIELD_SIZE, INITIAL_VEHICLE_POSITIONS, TARGETS

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
FINAL = FIGURES / "final_paper_20261122"
P1_GRID = FIGURES / "p1_t1_observable_grid_0p5m.npz"
P1_CIRCLE = FIGURES / "p1_t1_circle_candidates_1deg.csv"
P1_DEPLOYMENT = FIGURES / "p1_t1_vehicle_deployment_1deg.csv"
P1_SUMMARY = FIGURES / "p1_t1_circle_summary_1deg.json"
P2_SUMMARY = FIGURES / "p2_t2_optimum_summary_v2.json"
P3_RESULTS = FIGURES / "p3_verified_20261122" / "p3_analysis_results.json"


def _save(fig, path: Path) -> None:
    with path.open("xb") as stream:
        fig.savefig(stream, dpi=200, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def export_p1_observable() -> None:
    with np.load(P1_GRID) as grid:
        fig, ax = plot_field(observable=grid["observable"],
                             x_values=grid["x_values"], y_values=grid["y_values"])
    ax.set_title("P1: T1 observable region")
    _save(fig, FINAL / "p1_observable_region.png")


def export_p1_deployment() -> None:
    with np.load(P1_GRID) as grid:
        fig, ax = plot_field(observable=grid["observable"],
                             x_values=grid["x_values"], y_values=grid["y_values"])
    circle = _load_csv(P1_CIRCLE)
    feasible = [r for r in circle if r["feasible"].lower() == "true"]
    xy = np.array([(float(r["x_east_m"]), float(r["y_north_m"])) for r in feasible])
    all_xy = np.array([(float(r["x_east_m"]), float(r["y_north_m"])) for r in circle])
    ax.plot(all_xy[:, 0], all_xy[:, 1], color=COLORS["building"], lw=1.0,
            ls="--", label="Theoretical radius", zorder=6)
    ax.scatter(xy[:, 0], xy[:, 1], s=10, color=COLORS["feasible"],
               edgecolors="#333333", linewidths=0.15, label="Feasible circle samples", zorder=7)
    summary = json.loads(P1_SUMMARY.read_text(encoding="utf-8"))
    best = summary["best_screening_row"]
    ax.plot([best["start_x_m"], best["station_x_m"]],
            [best["start_y_m"], best["station_y_m"]],
            color=COLORS["vehicle"], ls="--", lw=1.6,
            label="V4 verified straight route", zorder=7)
    ax.scatter([best["start_x_m"]], [best["start_y_m"]], marker="s", s=42,
               color=COLORS["vehicle"], edgecolors="white", linewidths=.6, zorder=8)
    ax.scatter([best["station_x_m"]], [best["station_y_m"]], marker="*", s=125,
               color=COLORS["vehicle"], edgecolors="#333333", linewidths=0.8,
               label="Best discrete deployment (5.0645 s)", zorder=9)
    ax.set_title("P1: T1 deployment candidates")
    original_handles, original_labels = ax.get_legend_handles_labels()
    overlays = [
        Patch(facecolor=COLORS["feasible"], label="Observable (sampled)"),
        Patch(facecolor=COLORS["infeasible"], label="Not observable (sampled)"),
        Patch(facecolor=COLORS["building"], label="Buildings"),
        *[handle for handle, label in zip(original_handles, original_labels)
          if label not in {"Observable (sampled)", "Not observable (sampled)", "Buildings"}],
    ]
    ax.legend(handles=overlays, loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=2, frameon=True)
    _save(fig, FINAL / "p1_deployment.png")


def _draw_buildings(ax) -> None:
    for building in BUILDINGS:
        ax.add_patch(Rectangle((building["x_min"], building["y_min"]),
                               building["x_max"] - building["x_min"],
                               building["y_max"] - building["y_min"],
                               facecolor=COLORS["building"], edgecolor="white",
                               linewidth=0.8, zorder=3))
        ax.text((building["x_min"] + building["x_max"]) / 2,
                (building["y_min"] + building["y_max"]) / 2,
                f"B{building['id']}", color="white", ha="center", va="center", zorder=4)


def export_p2_geometry() -> None:
    data = json.loads(P2_SUMMARY.read_text(encoding="utf-8"))
    winner = data["winner"]
    target = TARGETS[1]
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    _draw_buildings(ax)
    p, q = winner["station_a"], winner["station_b"]
    t = (target["x"], target["y"])
    fleet = {v["id"]: (v["x"], v["y"]) for v in INITIAL_VEHICLE_POSITIONS}
    for key, point, style in (("vehicle_a", p, "-"), ("vehicle_b", q, "--")):
        start = fleet[winner[key]]
        ax.plot([start[0], point[0]], [start[1], point[1]],
                color=COLORS["vehicle"], ls=style, lw=1.5, alpha=.75,
                label=f"V{winner[key]} route", zorder=4)
        ax.scatter([start[0]], [start[1]], color=COLORS["vehicle"],
                   marker="x", s=55, zorder=5)
    ax.plot([p[0], t[0]], [p[1], t[1]], color=COLORS["vehicle"], lw=1.8,
            label="V1 bearing line", zorder=2)
    ax.plot([q[0], t[0]], [q[1], t[1]], color=COLORS["vehicle"], lw=1.8,
            ls="--", label="V3 bearing line", zorder=2)
    ax.scatter([p[0], q[0]], [p[1], q[1]], marker="o", s=65,
               facecolors="white", edgecolors=COLORS["vehicle"], linewidths=2,
               label="Optimal stations", zorder=5)
    ax.scatter([t[0]], [t[1]], marker="*", s=145, color=COLORS["target"],
               edgecolors="#333333", linewidths=0.6, label="T2 target", zorder=6)
    ax.set(xlim=(0, FIELD_SIZE), ylim=(0, FIELD_SIZE),
           xlabel="x (m, east)", ylabel="y (m, north)",
           title=f"P2(1): optimal two-station geometry (RMSE {winner['rmse_m']:.4f} m)")
    ax.set_aspect("equal")
    handles = [
        Patch(facecolor=COLORS["building"], label="Buildings"),
        Line2D([], [], color=COLORS["vehicle"], ls="-", label="V1 route / bearing"),
        Line2D([], [], color=COLORS["vehicle"], ls="--", label="V3 route / bearing"),
        Line2D([], [], color=COLORS["vehicle"], marker="o", markerfacecolor="white",
               ls="none", label="Optimal stations"),
        Line2D([], [], color=COLORS["target"], marker="*", ls="none", label="T2 target"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, -.13),
              ncol=2, frameon=True)
    _save(fig, FINAL / "p2_intersection_geometry.png")


def export_p2_accuracy() -> None:
    data = json.loads(P2_SUMMARY.read_text(encoding="utf-8"))
    winner = data["winner"]
    r1, r2 = winner["r1_m"], winner["r2_m"]
    sigma = math.radians(1.0)
    angles = np.linspace(0.01, 179.99, 1200)
    values = sigma * math.hypot(r1, r2) / np.abs(np.sin(np.deg2rad(angles)))
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    ax.plot(angles, values, color=COLORS["vehicle"], lw=2.2,
            label="Fixed target ranges")
    for angle in (1, 5, 90, 175, 179):
        value = sigma * math.hypot(r1, r2) / abs(math.sin(math.radians(angle)))
        ax.scatter(angle, value, color=COLORS["feasible"], s=32, zorder=3)
    ax.axvline(90, color=COLORS["building"], lw=1, ls="--", label="90°")
    ax.set(xlim=(0, 180), ylim=(0.1, 100), yscale="log",
           xlabel="Intersection angle γ (deg)",
           ylabel="Horizontal RMSE (m, log scale)",
           title="P2(1): bearing-intersection sensitivity")
    ax.legend(loc="upper center", frameon=False)
    ax.text(.02, .83, "γ=0°/180°: degenerate", ha="left", va="center",
            transform=ax.transAxes, fontsize=10,
            bbox=dict(facecolor="white", edgecolor="none", alpha=.88))
    _save(fig, FINAL / "p2_accuracy.png")


def export_p3() -> None:
    data = json.loads(P3_RESULTS.read_text(encoding="utf-8"))
    linear_s = data["linear_s_max_m"]
    exact_s = data["exact_s_max_m"]
    from geometry_B.p3.analysis import exact_probability, sigma_position, theoretical_propagation
    s_grid = np.linspace(0, max(80, exact_s * 1.35), 85)
    first = np.array([theoretical_propagation(sigma_position(float(s)))["probability"] for s in s_grid])
    exact = np.array([exact_probability(sigma_position(float(s))) for s in s_grid])
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    ax.plot(s_grid, first, color=COLORS["vehicle"], lw=2, label="First-order normal")
    ax.plot(s_grid, exact, color=COLORS["target"], ls="--", lw=2, label="Exact angle integral")
    ax.axhline(.95, color=COLORS["building"], ls=":", lw=1.5, label="Requirement: 95%")
    ax.axvline(exact_s, color=COLORS["feasible"], ls="-.", lw=1.2,
               label=f"Exact limit ≈ {exact_s:.4f} m")
    ax.set(xlabel="Cumulative travel distance s (m)",
           ylabel="P(|effective bearing error| ≤ 5°)",
           ylim=(max(0, min(first.min(), exact.min()) - .025), 1.005),
           title="P3: bearing-accuracy probability")
    ax.legend(loc="lower left", frameon=True)
    _save(fig, FINAL / "p3_error.png")

    bound = data["exact_a_plus_80b_bound_m"]
    linear_bound = data["linear_a_plus_80b_bound_m"]
    b = np.linspace(0, bound / 80, 200)
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    ax.fill_between(b, 0, bound - 80 * b, color=COLORS["feasible"], alpha=.22,
                    label="Exact-model feasible")
    ax.plot(b, bound - 80 * b, color=COLORS["feasible"], lw=2,
            label="a + 80b = exact bound")
    ax.plot(b, linear_bound - 80 * b, color=COLORS["vehicle"], ls="--", lw=1.8,
            label="First-order boundary")
    ax.set(xlabel="Localization growth coefficient b (m/m)",
           ylabel="Initial localization SD a (m)",
           xlim=(0, bound / 80 * 1.06), ylim=(0, bound * 1.07),
           title="P3: feasible localization parameters at s=80 m")
    ax.legend(loc="upper right", frameon=True)
    _save(fig, FINAL / "p3_parameter_constraints.png")

    labels = ["s=0 m", f"s={linear_s:.2f} m\n(first-order limit)", "s=80 m"]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    bottom = np.zeros(3)
    for key, label, color, hatch in (("position", "Vehicle localization", COLORS["vehicle"], ""),
                                      ("zero", "Gimbal zero offset", COLORS["target"], "//"),
                                      ("control", "Gimbal control", COLORS["feasible"], "\\\\")):
        heights = np.array([data["contributions"][name][key] * 100
                            for name in ("s=0", "s=linear boundary", "s=80")])
        ax.bar(x, heights, bottom=bottom, width=.62, color=color, hatch=hatch,
               edgecolor="white", linewidth=1, label=label)
        bottom += heights
    ax.set(xticks=x, xticklabels=labels,
           ylabel="Share of first-order angular variance (%)", ylim=(0, 105),
           title="P3: error-source variance contributions")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.17), ncol=3,
              frameon=False)
    _save(fig, FINAL / "p3_variance_contributions.png")


def main() -> None:
    apply_figure_style()
    FINAL.mkdir(parents=True, exist_ok=True)
    for path in (P1_GRID, P1_CIRCLE, P1_DEPLOYMENT, P1_SUMMARY, P2_SUMMARY, P3_RESULTS):
        if not path.exists():
            raise FileNotFoundError(path)
    export_p1_observable()
    export_p1_deployment()
    export_p2_geometry()
    export_p2_accuracy()
    export_p3()
    print("Exported 7 standardized paper figures to figures/.")


if __name__ == "__main__":
    main()
