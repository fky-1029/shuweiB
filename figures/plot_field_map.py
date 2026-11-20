"""
Field layout figure for ShuWeiCup 2026 Problem B.

Draws the 100x100 m field, 5 buildings, 5 vehicles, 3 targets, dispatch center,
and the alert azimuth lines. Output: field_map.png (next to this script).

Data source (single source of truth): shared/constants.md
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive: only save to file
import matplotlib.pyplot as plt
from matplotlib import patches

# --- data (from shared/constants.md) ---
BUILDINGS = [  # name, x0, y0, w, h, height(m)
    ("B1", 22, 16, 12, 10, 20),
    ("B2", 63, 59, 16, 12, 28),
    ("B3", 10, 65, 14, 11, 12),
    ("B4", 72, 22, 14, 12, 24),
    ("B5", 41, 38, 10, 8, 32),
]
VEHICLES = {"V1": (15, 14), "V2": (88, 10), "V3": (14, 86), "V4": (88, 68), "V5": (50, 93)}
DISPATCH = (50, 50)
TARGETS = {"T1": (30, 40, 45), "T2": (150, 45, 35), "T3": (285, 38, 55)}  # theta(deg), R(m), H(m)

fig, ax = plt.subplots(figsize=(7.5, 7.5))

# field boundary
ax.plot([0, 100, 100, 0, 0], [0, 0, 100, 100, 0], "k-", lw=1.5)

# buildings
for name, x0, y0, w, h, hgt in BUILDINGS:
    ax.add_patch(patches.Rectangle((x0, y0), w, h, fc="0.72", ec="0.25", lw=1))
    ax.text(x0 + w / 2, y0 + h / 2, f"{name}\n{hgt} m", ha="center", va="center", fontsize=8)

# vehicles
for name, (x, y) in VEHICLES.items():
    ax.plot(x, y, "s", color="#1f77b4", ms=8)
    ax.text(x, y + 2.5, name, ha="center", fontsize=8, color="#1f77b4")

# dispatch center
ax.plot(*DISPATCH, "ko", ms=6)
ax.text(50, 46.5, "O (50,50)", ha="center", va="top", fontsize=8)

# targets + alert azimuth lines (dashed, from O through target)
for name, (theta, R, H) in TARGETS.items():
    th = np.deg2rad(theta)
    x = 50 + R * np.cos(th)
    y = 50 + R * np.sin(th)
    ax.plot(x, y, "^", color="#d62728", ms=10)
    ax.text(x, y + 2.5, name, ha="center", fontsize=8, color="#d62728")
    ax.plot([50, 50 + (R + 30) * np.cos(th)], [50, 50 + (R + 30) * np.sin(th)],
            "--", color="#d62728", alpha=0.45, lw=1)

ax.set_xlim(-4, 104)
ax.set_ylim(-4, 104)
ax.set_aspect("equal")
ax.set_xlabel("x (m, east)")
ax.set_ylabel("y (m, north)")
ax.set_title("Field layout: buildings, vehicles, targets and alert azimuths")
ax.grid(True, alpha=0.3)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "field_map.png")
plt.tight_layout()
plt.savefig(out, dpi=200)
print("saved:", out)
