"""Career milestone overlays for trajectory plots."""

from __future__ import annotations

import re
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

_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{1,2}))?$")


def load_milestones(root: Path) -> dict:
    path = root / "trajectory/milestones.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_year_position(value, *, edge: str = "start") -> float:
    """Map YYYY or YYYY-MM to fractional year on the plot x-axis."""
    if value is None:
        raise ValueError("missing date")
    if isinstance(value, (int, float)):
        year = int(value)
        if edge == "end":
            return float(year) + 1.0
        return float(year)

    text = str(value).strip()
    match = _DATE_RE.match(text)
    if not match:
        raise ValueError(f"invalid milestone date: {value!r}")

    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else None
    if month is None:
        if edge == "end":
            return float(year) + 1.0
        return float(year)

    if edge == "start":
        return year + (month - 1) / 12.0
    if edge == "mid":
        return year + (month - 0.5) / 12.0
    return year + month / 12.0


def apply_milestones(ax: Axes, root: Path, xmax: int) -> None:
    data = load_milestones(root)
    ymin, ymax = ax.get_ylim()
    bands = data.get("bands") or []

    for idx, band in enumerate(bands):
        start = parse_year_position(band["start"], edge="start")
        if idx + 1 < len(bands):
            # Adjacent bands: end exactly where the next position starts (no overlap).
            end_val = parse_year_position(bands[idx + 1]["start"], edge="start")
        else:
            end = band.get("end")
            end_val = float(xmax) + 0.5 if end is None else parse_year_position(end, edge="start")
        color = BAND_COLORS[idx % len(BAND_COLORS)]
        ax.axvspan(start, end_val, color=color, alpha=0.55, zorder=0)
        mid = (start + end_val) / 2
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
        when = point.get("date", point.get("year"))
        x = parse_year_position(when, edge="mid")
        kind = (point.get("kind") or "academic").lower()
        if kind == "personal":
            color = "#9a3412"
            linestyle = ":"
            alpha = 0.85
        else:
            color = "#4b5563"
            linestyle = "--"
            alpha = 0.8
        ax.axvline(x, color=color, linestyle=linestyle, linewidth=0.9, alpha=alpha, zorder=1)
        ax.text(
            x,
            ymax * 0.88,
            point.get("label", ""),
            ha="center",
            va="top",
            fontsize=7,
            color=color,
            rotation=90,
            zorder=2,
        )

    ax.set_ylim(ymin, ymax)
