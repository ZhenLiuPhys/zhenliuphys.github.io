"""Matplotlib figure builders for career trajectory plots."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from trajectory_lib.load_data import cumulative, fill_year_grid
from trajectory_lib.milestones import apply_milestones

FIGSIZE = (18, 3.5)
DPI = 160

SERIES_ORDER = {
    "pubs": ["Refereed", "Editor", "Contributor", "Total"],
    "talks": [
        "seminar",
        "plenary",
        "workshop",
        "colloquium",
        "lecture",
        "other",
        "Total",
    ],
    "service": ["Chair", "Workshop organizer", "Committee", "Session convener", "Total"],
    "letters": [
        "Grad RL",
        "Postdoc RL",
        "Faculty RL",
        "Industrial RL",
        "Faculty promotion",
        "Fellowships & programs",
        "Faculty award nominations",
        "Immigration",
        "Other",
        "Total",
    ],
}


def _style_ax(ax, years: list[int], title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11, pad=8)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=18))
    ax.grid(True, axis="y", alpha=0.25, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_multi_series(
    years: list[int],
    series: dict[str, dict[int, int]],
    *,
    order: list[str],
    title: str,
    ylabel: str,
    root: Path,
    out_path: Path,
    cumulative_mode: bool = False,
) -> None:
    grid = fill_year_grid(series, years)
    fig, ax = plt.subplots(figsize=FIGSIZE)

    colors = plt.cm.tab10.colors
    for idx, name in enumerate(order):
        if name not in grid:
            continue
        values = grid[name]
        if cumulative_mode:
            values = cumulative(values)
        linewidth = 2.4 if name == "Total" else 1.5
        alpha = 1.0 if name == "Total" else 0.9
        linestyle = "-" if name != "Total" else "-"
        ax.plot(
            years,
            values,
            label=name,
            color=colors[idx % len(colors)],
            linewidth=linewidth,
            alpha=alpha,
            linestyle=linestyle,
            marker="o",
            markersize=3 if name != "Total" else 4,
        )

    mode_label = "Cumulative" if cumulative_mode else "Annual"
    _style_ax(ax, years, f"{title} ({mode_label})", ylabel)
    apply_milestones(ax, root, years[-1])
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def plot_letters_annual_stacked(
    years: list[int],
    series: dict[str, dict[int, int]],
    *,
    order: list[str],
    root: Path,
    out_path: Path,
) -> None:
    grid = fill_year_grid(series, years)
    types_order = [name for name in order if name != "Total" and name in grid]
    if not types_order:
        return

    fig, ax = plt.subplots(figsize=FIGSIZE)
    colors = plt.cm.tab10.colors
    bottoms = [0] * len(years)

    for idx, name in enumerate(types_order):
        values = grid[name]
        ax.bar(
            years,
            values,
            bottom=bottoms,
            width=0.72,
            label=name,
            color=colors[idx % len(colors)],
            alpha=0.9,
            edgecolor="white",
            linewidth=0.4,
        )
        bottoms = [b + v for b, v in zip(bottoms, values)]

    if "Total" in grid:
        totals = grid["Total"]
        for x, t in zip(years, totals):
            if t:
                ax.text(x, t + 0.05, str(t), ha="center", va="bottom", fontsize=7, color="#333")

    _style_ax(ax, years, "Recommendation letters (Annual, by type)", "Count")
    apply_milestones(ax, root, years[-1])
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def plot_citations_by_pub_year(
    years: list[int],
    annual_citations: dict[int, int],
    root: Path,
    out_path: Path,
    snapshot_date: str,
) -> None:
    values = [annual_citations.get(y, 0) for y in years]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.bar(years, values, width=0.7, color="#4c72b0", alpha=0.85, label="Citations (snapshot)")
    _style_ax(
        ax,
        years,
        f"Refereed citations by publication year (inSPIRE snapshot {snapshot_date})",
        "Citations",
    )
    apply_milestones(ax, root, years[-1])
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def plot_citations_cumulative_stock(
    years: list[int],
    stock: dict[int, int],
    root: Path,
    out_path: Path,
    snapshot_date: str,
) -> None:
    values = [stock.get(y, 0) for y in years]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(years, values, color="#2a5a8a", linewidth=2.2, marker="o", markersize=4)
    _style_ax(
        ax,
        years,
        f"Refereed citation stock through publication year (inSPIRE snapshot {snapshot_date})",
        "Cumulative citations",
    )
    apply_milestones(ax, root, years[-1])
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def write_summary_csv(
    years: list[int],
    tables: dict[str, dict[str, dict[int, int]]],
    out_path: Path,
) -> None:
    """Write year x all series columns (annual counts only)."""
    import csv

    columns: list[str] = []
    for group, series in tables.items():
        for name in series:
            col = f"{group}_{name}"
            columns.append(col)

    fieldnames = ["year"] + columns
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for y in years:
            row: dict = {"year": y}
            for group, series in tables.items():
                for name, counts in series.items():
                    row[f"{group}_{name}"] = counts.get(y, 0)
            writer.writerow(row)


def today_iso() -> str:
    return date.today().isoformat()
