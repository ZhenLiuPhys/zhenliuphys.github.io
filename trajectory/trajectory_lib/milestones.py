"""Career milestone overlays for trajectory plots."""

from __future__ import annotations

from pathlib import Path

import yaml
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

BAND_COLORS = [
    "#e8eef5",
    "#dce8f0",
    "#e5e0f0",
    "#e0f0e5",
    "#f0e8dc",
]


def load_milestones(root: Path) -> dict:
    path = root / "trajectory/milestones.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def apply_milestones(ax: Axes, root: Path, xmax: int) -> None:
    data = load_milestones(root)
    ymin, ymax = ax.get_ylim()

    for idx, band in enumerate(data.get("bands") or []):
        start = int(band["start"])
        end = band.get("end")
        end_val = float(xmax + 0.5) if end is None else int(end) + 0.5
        color = BAND_COLORS[idx % len(BAND_COLORS)]
        ax.axvspan(start - 0.5, end_val, color=color, alpha=0.55, zorder=0)
        mid = (start + (xmax if end is None else int(end))) / 2
        ax.text(
            mid,
            ymax * 0.97,
            band.get("label", ""),
            ha="center",
            va="top",
            fontsize=7,
            color="#4a5568",
            rotation=0,
            zorder=1,
        )

    for point in data.get("points") or []:
        year = int(point["year"])
        ax.axvline(year, color="#6b7280", linestyle="--", linewidth=0.9, alpha=0.75, zorder=1)
        ax.text(
            year,
            ymax * 0.88,
            point.get("label", ""),
            ha="center",
            va="top",
            fontsize=7,
            color="#374151",
            rotation=90,
            zorder=2,
        )

    ax.set_ylim(ymin, ymax)
