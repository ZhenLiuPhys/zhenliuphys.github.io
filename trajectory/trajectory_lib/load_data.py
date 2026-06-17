"""Load publications, talks, and service data for trajectory plots."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import yaml

PUB_SECTION_LABELS = {
    "refereed_journals": "Refereed",
    "other_publications_editor": "Editor",
    "other_publications_contributor": "Contributor",
}

TALK_CATEGORIES = [
    "seminar",
    "plenary",
    "workshop",
    "colloquium",
    "lecture",
    "other",
]

SERVICE_ROLES = [
    "Chair",
    "Workshop organizer",
    "Committee",
    "Session convener",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_publications(root: Path | None = None) -> list[dict]:
    path = (root or repo_root()) / "data/publications.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def load_talks(root: Path | None = None) -> list[dict]:
    path = (root or repo_root()) / "data/talks.yaml"
    talks = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [t for t in talks if not t.get("placeholder")]


def load_service(root: Path | None = None) -> dict:
    path = (root or repo_root()) / "data/source/service.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def year_range_from_series(
    series_list: list[dict[str, dict[int, int]]],
    *,
    xmin: int = 2009,
    xmax_floor: int = 2026,
) -> list[int]:
    years: list[int] = []
    for series in series_list:
        for counts in series.values():
            years.extend(counts.keys())
    data_max = max(years) if years else xmax_floor
    upper = max(data_max, xmax_floor)
    return list(range(xmin, upper + 1))


def counts_by_year(items: list[dict], key_fn) -> dict[int, int]:
    counts: Counter[int] = Counter()
    for item in items:
        year = item.get("year")
        if year is None:
            continue
        bucket = key_fn(item)
        if bucket is None:
            continue
        counts[int(year)] += 1
    return dict(counts)


def publication_series(pubs: list[dict]) -> dict[str, dict[int, int]]:
    by_section: dict[str, dict[int, int]] = {label: defaultdict(int) for label in PUB_SECTION_LABELS.values()}
    for pub in pubs:
        section = pub.get("section") or ""
        label = PUB_SECTION_LABELS.get(section)
        if not label:
            continue
        year = int(pub["year"])
        by_section[label][year] += 1
    total: dict[int, int] = defaultdict(int)
    for label, counts in by_section.items():
        for year, n in counts.items():
            total[year] += n
    result = {k: dict(v) for k, v in by_section.items()}
    result["Total"] = dict(total)
    return result


def talk_series(talks: list[dict]) -> dict[str, dict[int, int]]:
    by_cat: dict[str, dict[int, int]] = {c: defaultdict(int) for c in TALK_CATEGORIES}
    for talk in talks:
        cat = (talk.get("category") or "other").lower()
        if cat == "scheduled":
            cat = "other"
        if cat not in by_cat:
            cat = "other"
        year = int(talk["year"])
        by_cat[cat][year] += 1
    total: dict[int, int] = defaultdict(int)
    for counts in by_cat.values():
        for year, n in counts.items():
            total[year] += n
    result = {c: dict(by_cat[c]) for c in TALK_CATEGORIES}
    result["Total"] = dict(total)
    return result


def refereed_publications(pubs: list[dict]) -> list[dict]:
    return [p for p in pubs if p.get("section") == "refereed_journals"]


def fill_year_grid(series: dict[str, dict[int, int]], years: list[int]) -> dict[str, list[int]]:
    return {name: [counts.get(y, 0) for y in years] for name, counts in series.items()}


def cumulative(values: list[int]) -> list[int]:
    out: list[int] = []
    running = 0
    for v in values:
        running += v
        out.append(running)
    return out
