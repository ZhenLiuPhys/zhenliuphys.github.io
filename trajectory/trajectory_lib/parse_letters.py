"""Parse local recommendation-letter log for trajectory plots."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

DEFAULT_LETTER_TYPES: dict[str, str] = {
    "postdoc_rl": "Postdoc RL",
    "faculty_rl": "Faculty RL",
    "grad_rl": "Grad RL",
    "industrial_rl": "Industrial RL",
    "faculty_promotion": "Faculty promotion",
    "umn_award_nomination": "UMN award nomination",
    "university_fellowship_rl": "University fellowship RL",
    "summer_school_rl": "Summer school RL",
    "nsf_fellowship_rl": "NSF fellowship RL",
    "nsf_reu_undergrad_rl": "NSF REU undergrad RL",
    "fellowship_nomination": "Fellowship nomination",
    "national_award_nomination": "National award nomination",
    "international_award_nomination": "International award nomination",
    "visa_letter": "Visa letter",
    "greencard_letter": "Greencard letter",
    "workshop_program": "Workshop / program letter",
    "prize_nomination": "Prize nomination",
    "other": "Other",
}

# Fine-grained labels (detail CSV / console); plots use LETTER_PLOT_GROUPS below.
LETTER_SERIES_ORDER = [
    "Grad RL",
    "Postdoc RL",
    "Faculty RL",
    "Industrial RL",
    "Faculty promotion",
    "UMN award nomination",
    "University fellowship RL",
    "Summer school RL",
    "NSF fellowship RL",
    "NSF REU undergrad RL",
    "Fellowship nomination",
    "National award nomination",
    "International award nomination",
    "Visa letter",
    "Greencard letter",
    "Workshop / program letter",
    "Prize nomination",
    "Other",
    "Total",
]

FELLOWSHIPS_PROGRAMS_TYPES = frozenset(
    {
        "umn_award_nomination",
        "university_fellowship_rl",
        "summer_school_rl",
        "workshop_program",
        "nsf_fellowship_rl",
        "nsf_reu_undergrad_rl",
        "fellowship_nomination",
        "prize_nomination",
    }
)

FACULTY_AWARD_NOMINATION_TYPES = frozenset(
    {
        "national_award_nomination",
        "international_award_nomination",
    }
)

IMMIGRATION_TYPES = frozenset({"visa_letter", "greencard_letter"})

# The counted log starts here. Earlier years may be recorded locally and are skipped.
LETTER_COUNT_FROM_YEAR = 2020

CAREER_TYPES = frozenset(
    {
        "grad_rl",
        "postdoc_rl",
        "faculty_rl",
        "industrial_rl",
        "faculty_promotion",
    }
)

LETTER_PLOT_GROUPS = {
    "grad_rl": "Grad RL",
    "postdoc_rl": "Postdoc RL",
    "faculty_rl": "Faculty RL",
    "industrial_rl": "Industrial RL",
    "faculty_promotion": "Faculty promotion",
    **{t: "Fellowships & programs" for t in FELLOWSHIPS_PROGRAMS_TYPES},
    **{t: "Faculty award nominations" for t in FACULTY_AWARD_NOMINATION_TYPES},
    **{t: "Immigration" for t in IMMIGRATION_TYPES},
    "other": "Other",
}

LETTER_PLOT_ORDER = [
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
]


def letters_path(root: Path) -> Path:
    return root / "trajectory/data/recommendation_letters.yaml"


def example_path(root: Path) -> Path:
    return root / "trajectory/recommendation_letters.example.yaml"


def load_recommendation_letters(root: Path) -> dict:
    path = letters_path(root)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.relative_to(root)} — copy {example_path(root).relative_to(root)} "
            "and add your records (local only, not on GitHub)."
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("people"):
        raise ValueError(f"No people entries in {path}")
    return data


def _type_labels(data: dict) -> dict[str, str]:
    custom = data.get("letter_types") or {}
    labels = dict(DEFAULT_LETTER_TYPES)
    labels.update(custom)
    return labels


def plot_group_for_type(type_id: str, data: dict | None = None) -> str:
    if data:
        overrides = data.get("plot_groups") or {}
        if type_id in overrides:
            return overrides[type_id]
    return LETTER_PLOT_GROUPS.get(type_id, type_id.replace("_", " ").title())


def letter_detail_rows(data: dict) -> list[dict]:
    """Flat rows: one row per person × type × year."""
    labels = _type_labels(data)
    rows: list[dict] = []
    for person in data.get("people", []):
        name = (person.get("name") or "").strip()
        if not name:
            continue
        for entry in person.get("entries", []):
            type_id = entry.get("type") or "other"
            label = labels.get(type_id, type_id.replace("_", " ").title())
            note = (entry.get("note") or "").strip()
            plot_group = plot_group_for_type(type_id, data)
            for year in entry.get("years", []) or []:
                year_i = int(year)
                if year_i < LETTER_COUNT_FROM_YEAR:
                    continue
                rows.append(
                    {
                        "year": year_i,
                        "type_id": type_id,
                        "type": label,
                        "plot_group": plot_group,
                        "name": name,
                        "note": note,
                    }
                )
    rows.sort(key=lambda r: (r["year"], r["plot_group"], r["type"], r["name"]))
    return rows


def letter_series(data: dict) -> dict[str, dict[int, int]]:
    labels = _type_labels(data)
    label_set = set(labels.values())
    by_type: dict[str, dict[int, int]] = {label: defaultdict(int) for label in label_set}
    total: dict[int, int] = defaultdict(int)

    for row in letter_detail_rows(data):
        label = row["type"]
        year = row["year"]
        by_type.setdefault(label, defaultdict(int))
        by_type[label][year] += 1
        total[year] += 1

    ordered_labels = [lbl for lbl in LETTER_SERIES_ORDER if lbl in by_type and lbl != "Total"]
    for lbl in sorted(by_type):
        if lbl not in ordered_labels:
            ordered_labels.append(lbl)

    result = {lbl: dict(by_type[lbl]) for lbl in ordered_labels if by_type[lbl]}
    result["Total"] = dict(total)
    return result


def letter_series_grouped(data: dict) -> dict[str, dict[int, int]]:
    by_group: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    total: dict[int, int] = defaultdict(int)

    for row in letter_detail_rows(data):
        group = row["plot_group"]
        year = row["year"]
        by_group[group][year] += 1
        total[year] += 1

    ordered = [g for g in LETTER_PLOT_ORDER if g != "Total" and by_group.get(g)]
    for g in sorted(by_group):
        if g not in ordered:
            ordered.append(g)

    result = {g: dict(by_group[g]) for g in ordered}
    result["Total"] = dict(total)
    return result


def write_letters_detail_csv(rows: list[dict], out_path: Path) -> None:
    import csv

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["year", "plot_group", "type_id", "type", "name", "note"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def print_letters_summary(
    rows: list[dict],
    grouped_series: dict[str, dict[int, int]],
    *,
    fine_series: dict[str, dict[int, int]] | None = None,
) -> None:
    total = sum(grouped_series.get("Total", {}).values())
    print(f"recommendation letters: {total} total across {len(rows)} person-year-type records")
    print("plot groups:")
    for label in LETTER_PLOT_ORDER:
        if label == "Total":
            continue
        counts = grouped_series.get(label)
        if not counts:
            continue
        print(f"  {label}: {sum(counts.values())}")
    if fine_series:
        print("fine types:")
        by_type = {k: sum(v.values()) for k, v in fine_series.items() if k != "Total"}
        for label, n in sorted(by_type.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {label}: {n}")
