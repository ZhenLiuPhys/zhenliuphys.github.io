"""Parse service.yaml lines into year + role counts."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from trajectory_lib.load_data import SERVICE_ROLES

YEAR_RE = re.compile(r"(19|20)\d{2}")
RANGE_RE = re.compile(r"(19|20)\d{2}\s*---+\s*((19|20)\d{2})")


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


def service_series(service: dict, root: Path | None = None) -> tuple[dict[str, dict[int, int]], list[str]]:
    overrides_path = None
    if root:
        overrides_path = root / "trajectory/data/service_overrides.yaml"
    return parse_service_entries(service, overrides_path)
