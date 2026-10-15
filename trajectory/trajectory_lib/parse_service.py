"""Parse service.yaml lines into year + role counts."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from datetime import date

from trajectory_lib.load_data import REVIEW_ROLES, SERVICE_ROLES

YEAR_RE = re.compile(r"(19|20)\d{2}")
FULL_YEAR_RE = re.compile(r"(?:19|20)\d{2}")
RANGE_RE = re.compile(r"(19|20)\d{2}\s*---+\s*((19|20)\d{2})")
OPEN_RANGE_RE = re.compile(r"((?:19|20)\d{2})\s*-\s*((?:19|20)\d{2})?")


def extract_year(line: str) -> int | None:
    range_match = RANGE_RE.search(line)
    if range_match:
        return int(range_match.group(1))
    match = YEAR_RE.search(line)
    return int(match.group()) if match else None


def classify_role(line: str, source: str) -> str | None:
    low = line.lower()
    if low.startswith("chair,"):
        return "Chair"
    if low.startswith("convener,"):
        return "Session convener"
    if low.startswith("panelist,"):
        return None
    if "scientific program committee" in low or low.startswith("academic committee"):
        return "Committee"
    if low.startswith("organizer,") or low.startswith("organizing committee") or low.startswith("local coordinator"):
        return "Workshop organizer"
    if source == "conference_sessions" and low.startswith("organizer,"):
        return "Session convener"
    return "Other"


def load_service_overrides(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def parse_service_entries(service: dict, overrides_path: Path | None = None) -> tuple[dict[str, dict[int, int]], list[str]]:
    overrides = load_service_overrides(overrides_path) if overrides_path else {}
    counts: dict[str, dict[int, int]] = {role: defaultdict(int) for role in SERVICE_ROLES}
    notes: list[str] = []

    sources = [
        ("workshops", service.get("workshops") or []),
        ("conference_sessions", service.get("conference_sessions") or []),
    ]

    for source_name, lines in sources:
        for idx, line in enumerate(lines):
            key = f"{source_name}:{idx}"
            override = overrides.get(key) or {}
            if override.get("skip"):
                notes.append(f"skipped override: {line[:70]}")
                continue
            year = override.get("year") or extract_year(line)
            role = override.get("role") or classify_role(line, source_name)
            if year is None:
                notes.append(f"no year: {line[:70]}")
                continue
            if role is None:
                notes.append(f"omitted panelist: {line[:70]}")
                continue
            if role == "Other":
                notes.append(f"unclassified ({source_name}): {line[:70]}")
                continue
            counts[role][int(year)] += 1

    total: dict[int, int] = defaultdict(int)
    for role_counts in counts.values():
        for year, n in role_counts.items():
            total[year] += n

    result = {role: dict(counts[role]) for role in SERVICE_ROLES}
    result["Total"] = dict(total)
    return result, notes


def _years_in_line(line: str) -> list[int]:
    return [int(y) for y in FULL_YEAR_RE.findall(line)]


def _expand_open_range(line: str, *, today_year: int | None = None) -> list[int] | None:
    match = OPEN_RANGE_RE.search(line)
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else (today_year or date.today().year)
    if end < start:
        return [start]
    return list(range(start, end + 1))


def _add_university_service(service: dict, counts: dict[str, dict[int, int]], notes: list[str]) -> None:
    for line in service.get("university_service") or []:
        years = _years_in_line(line)
        if not years:
            notes.append(f"undated university service: {line[:70]}")
            continue
        for year in dict.fromkeys(years):
            counts["University service"][year] += 1


def load_review_activity(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _counts_from_map(raw: dict | None) -> dict[int, int]:
    counts: dict[int, int] = {}
    for year, n in (raw or {}).items():
        counts[int(year)] = int(n)
    return counts


def review_series(service: dict, root: Path | None = None) -> tuple[dict[str, dict[int, int]], list[str]]:
    """Journal referee and grant counts are local (gitignored). Editorial follows the CV."""
    notes: list[str] = []
    counts: dict[str, dict[int, int]] = {role: {} for role in REVIEW_ROLES}
    activity_path = None
    if root:
        activity_path = root / "trajectory/data/referee_activity.yaml"
    activity = load_review_activity(activity_path) if activity_path else {}
    if activity_path and not activity_path.exists():
        notes.append("no trajectory/data/referee_activity.yaml — journal and grant counts omitted")
    counts["Journal referee"] = _counts_from_map(activity.get("journal_referee"))
    counts["Grant review"] = _counts_from_map(activity.get("grant_review"))

    editorial: dict[int, int] = defaultdict(int)
    for line in service.get("editorial_referee") or []:
        years = _expand_open_range(line) or _years_in_line(line)
        if not years:
            notes.append(f"undated editorial: {line[:70]}")
            continue
        for year in dict.fromkeys(years):
            editorial[year] += 1
    counts["Editorial"] = dict(editorial)

    total: dict[int, int] = defaultdict(int)
    for role_counts in counts.values():
        for year, n in role_counts.items():
            total[year] += n
    result = {role: dict(counts[role]) for role in REVIEW_ROLES}
    result["Total"] = dict(total)
    return result, notes


def service_series(service: dict, root: Path | None = None) -> tuple[dict[str, dict[int, int]], list[str]]:
    overrides_path = None
    if root:
        overrides_path = root / "trajectory/data/service_overrides.yaml"
    series, notes = parse_service_entries(service, overrides_path)
    # parse_service_entries builds Total before university service; recompute after.
    uni: dict[int, int] = defaultdict(int)
    uni_notes: list[str] = []
    holder = {"University service": uni}
    _add_university_service(service, holder, uni_notes)
    series["University service"] = dict(uni)
    total: dict[int, int] = defaultdict(int)
    for role in SERVICE_ROLES:
        for year, n in series.get(role, {}).items():
            total[year] += n
    series["Total"] = dict(total)
    return series, notes + uni_notes
