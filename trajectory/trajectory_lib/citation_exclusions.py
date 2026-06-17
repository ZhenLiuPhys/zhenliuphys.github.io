"""Citation exclusions and inventory for trajectory plots."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import yaml

from trajectory_lib.load_data import refereed_publications, load_publications

EXCLUSIONS_PATH = Path("trajectory/citation_exclusions.yaml")
REVIEW_HINT = re.compile(
    r"\bguide\b|\breview\b|\breport\b|white\s+paper|snowmass|proceedings|"
    r"community\s+vision|primer\b|overview\b|smasher'?s\s+guide",
    re.IGNORECASE,
)


def exclusions_path(root: Path) -> Path:
    return root / EXCLUSIONS_PATH


def load_exclusions(root: Path) -> set[str]:
    path = exclusions_path(root)
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = data.get("exclude_arxiv") or []
    return {str(x).strip() for x in items if str(x).strip()}


def is_review_candidate(title: str) -> bool:
    return bool(REVIEW_HINT.search(title or ""))


def build_citation_inventory(
    root: Path,
    cache: dict,
    exclusions: set[str] | None = None,
) -> list[dict]:
    exclusions = exclusions if exclusions is not None else load_exclusions(root)
    papers = cache.get("papers") or {}
    refereed = refereed_publications(load_publications(root))
    rows: list[dict] = []

    for pub in refereed:
        arxiv = (pub.get("arxiv") or "").strip()
        if not arxiv:
            continue
        meta = papers.get(arxiv) or {}
        title = pub.get("title") or meta.get("title") or ""
        citations = int(meta.get("citation_count") or 0)
        rows.append(
            {
                "arxiv": arxiv,
                "year": int(pub.get("year") or 0),
                "title": title,
                "citations": citations,
                "excluded": arxiv in exclusions,
                "review_candidate": is_review_candidate(title),
                "id": pub.get("id") or "",
            }
        )

    rows.sort(key=lambda r: (-r["citations"], -r["year"], r["arxiv"]))
    return rows


def filter_refereed_for_citations(refereed: list[dict], exclusions: set[str]) -> list[dict]:
    if not exclusions:
        return refereed
    return [p for p in refereed if (p.get("arxiv") or "").strip() not in exclusions]


def write_citation_inventory_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "arxiv",
        "year",
        "citations",
        "excluded",
        "review_candidate",
        "title",
        "id",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fields})


def print_citation_summary(rows: list[dict]) -> None:
    included = [r for r in rows if not r["excluded"]]
    excluded = [r for r in rows if r["excluded"]]
    flagged = [r for r in rows if r["review_candidate"] and not r["excluded"]]

    total_all = sum(r["citations"] for r in rows)
    total_in = sum(r["citations"] for r in included)
    total_out = sum(r["citations"] for r in excluded)

    print(f"Citation inventory: {len(rows)} refereed papers in cache")
    print(f"  Included: {len(included)} papers, {total_in} citations")
    if excluded:
        print(f"  Excluded: {len(excluded)} papers, {total_out} citations")
    else:
        print(f"  Excluded: 0 (edit trajectory/citation_exclusions.yaml to omit papers)")
    print(f"  All papers total: {total_all} citations")

    if flagged:
        print(f"\nReview/guide candidates still included ({len(flagged)}):")
        for r in flagged:
            print(f"  {r['citations']:5d}  {r['year']}  {r['arxiv']}  {r['title'][:65]}")

    print("\nTop 20 by citations (included only):")
    for r in included[:20]:
        mark = " *review?" if r["review_candidate"] else ""
        print(f"  {r['citations']:5d}  {r['year']}  {r['arxiv']}  {r['title'][:60]}{mark}")
