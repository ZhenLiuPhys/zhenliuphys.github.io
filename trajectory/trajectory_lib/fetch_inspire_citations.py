"""Fetch and cache inSPIRE citation counts for refereed publications."""

from __future__ import annotations

import csv
import time
from datetime import date
from pathlib import Path

import requests
import yaml

INSPIRE_API = "https://inspirehep.net/api/literature"
CACHE_VERSION = 1
HISTORY_DIR = Path("trajectory/citations_history")


def cache_path(root: Path) -> Path:
    return root / "trajectory/data/inspire_citations.yaml"


def history_dir(root: Path) -> Path:
    return root / HISTORY_DIR


def load_cache(root: Path) -> dict:
    path = cache_path(root)
    if not path.exists():
        return {"version": CACHE_VERSION, "fetched": None, "papers": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {"version": CACHE_VERSION, "fetched": None, "papers": {}}
    data.setdefault("papers", {})
    return data


def save_cache(root: Path, cache: dict) -> None:
    path = cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(cache, sort_keys=False, allow_unicode=True), encoding="utf-8")


def archive_snapshot(root: Path, cache: dict) -> Path | None:
    """Write/overwrite citations_history/{fetched}.yaml. Returns path or None if no date."""
    fetched = cache.get("fetched")
    if not fetched:
        return None
    out = history_dir(root) / f"{fetched}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": int(cache.get("version") or CACHE_VERSION),
        "fetched": fetched,
        "papers": cache.get("papers") or {},
    }
    out.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return out


def list_snapshots(root: Path) -> list[Path]:
    d = history_dir(root)
    if not d.exists():
        return []
    return sorted(d.glob("????-??-??.yaml"))


def load_snapshot(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {"version": CACHE_VERSION, "fetched": path.stem, "papers": {}}
    data.setdefault("papers", {})
    data.setdefault("fetched", path.stem)
    return data


def _paper_count(meta: dict | None) -> int:
    return int((meta or {}).get("citation_count") or 0)


def _included_papers(papers: dict, exclusions: set[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for arxiv, meta in (papers or {}).items():
        key = str(arxiv).strip()
        if not key or key in exclusions:
            continue
        out[key] = meta or {}
    return out


def snapshot_total(cache: dict, exclusions: set[str] | None = None) -> tuple[int, int]:
    """Return (total_citations, n_papers) for included papers."""
    exclusions = exclusions or set()
    included = _included_papers(cache.get("papers") or {}, exclusions)
    total = sum(_paper_count(m) for m in included.values())
    return total, len(included)


def growth_series(
    snapshots: list[dict],
    exclusions: set[str] | None = None,
    *,
    top_n: int = 15,
) -> dict:
    """Build totals, consecutive deltas, latest per-paper Δ, and cohort Δ.

    Returns dict with keys:
      summary_rows: list[{date, total, delta, n_papers}]
      latest_paper_deltas: list[{arxiv, title, year, prev, curr, delta}]
      latest_cohort_deltas: dict[year, delta]
      latest_interval: (prev_date, curr_date) | None
    """
    exclusions = exclusions or set()
    summary_rows: list[dict] = []
    prev_total: int | None = None
    prev_papers: dict[str, dict] = {}
    prev_date: str | None = None
    latest_paper_deltas: list[dict] = []
    latest_cohort_deltas: dict[int, int] = {}
    latest_interval: tuple[str, str] | None = None

    for snap in snapshots:
        fetched = str(snap.get("fetched") or "")
        papers = _included_papers(snap.get("papers") or {}, exclusions)
        total = sum(_paper_count(m) for m in papers.values())
        delta = 0 if prev_total is None else total - prev_total
        summary_rows.append(
            {
                "date": fetched,
                "total": total,
                "delta": delta,
                "n_papers": len(papers),
            }
        )

        if prev_date is not None:
            all_keys = set(prev_papers) | set(papers)
            paper_rows: list[dict] = []
            cohort: dict[int, int] = {}
            for arxiv in all_keys:
                prev_meta = prev_papers.get(arxiv) or {}
                curr_meta = papers.get(arxiv) or {}
                prev_c = _paper_count(prev_meta)
                curr_c = _paper_count(curr_meta)
                d = curr_c - prev_c
                if d == 0 and arxiv in prev_papers and arxiv in papers:
                    continue
                meta = curr_meta or prev_meta
                year = int(meta.get("year") or 0)
                paper_rows.append(
                    {
                        "arxiv": arxiv,
                        "title": meta.get("title") or "",
                        "year": year,
                        "prev": prev_c,
                        "curr": curr_c,
                        "delta": d,
                    }
                )
                if year:
                    cohort[year] = cohort.get(year, 0) + d
            paper_rows.sort(key=lambda r: (-abs(r["delta"]), -r["delta"], r["arxiv"]))
            latest_paper_deltas = paper_rows[:top_n]
            latest_cohort_deltas = dict(sorted(cohort.items()))
            latest_interval = (prev_date, fetched)

        prev_total = total
        prev_papers = papers
        prev_date = fetched

    return {
        "summary_rows": summary_rows,
        "latest_paper_deltas": latest_paper_deltas,
        "latest_cohort_deltas": latest_cohort_deltas,
        "latest_interval": latest_interval,
    }


def write_growth_summary_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["date", "total", "delta", "n_papers"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fields})


def print_citation_history(root: Path, exclusions: set[str] | None = None) -> None:
    paths = list_snapshots(root)
    if not paths:
        print("No citation history snapshots in trajectory/citations_history/")
        return
    print(f"Citation history ({len(paths)} snapshots):")
    prev_total: int | None = None
    for path in paths:
        snap = load_snapshot(path)
        total, n = snapshot_total(snap, exclusions)
        delta = "" if prev_total is None else f"  (Δ {total - prev_total:+d})"
        print(f"  {snap.get('fetched')}: {total} citations, {n} papers{delta}")
        prev_total = total


def fetch_citation_for_arxiv(arxiv: str, session: requests.Session) -> int:
    query = f"arxiv:{arxiv}"
    resp = session.get(
        INSPIRE_API,
        params={"q": query, "size": 1, "fields": "citation_count"},
        timeout=30,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", {}).get("hits", [])
    if not hits:
        return 0
    meta = hits[0].get("metadata") or {}
    return int(meta.get("citation_count") or 0)


def ensure_citations(
    refereed: list[dict],
    root: Path,
    *,
    refresh: bool = False,
    archive: bool | None = None,
) -> dict:
    """Fetch/update working cache. Archive to citations_history when refresh (default) or archive=True."""
    if archive is None:
        archive = refresh
    cache = load_cache(root)
    papers: dict = cache.setdefault("papers", {})
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    updated = False
    for pub in refereed:
        arxiv = (pub.get("arxiv") or "").strip()
        pub_id = pub.get("id") or arxiv
        if not arxiv:
            continue
        if not refresh and arxiv in papers:
            continue
        try:
            count = fetch_citation_for_arxiv(arxiv, session)
        except requests.RequestException as exc:
            print(f"WARNING: inSPIRE fetch failed for {arxiv}: {exc}")
            count = papers.get(arxiv, {}).get("citation_count", 0)
        papers[arxiv] = {
            "arxiv": arxiv,
            "id": pub_id,
            "title": pub.get("title"),
            "year": int(pub.get("year") or 0),
            "citation_count": count,
        }
        updated = True
        time.sleep(0.35)

    if updated or not cache.get("fetched"):
        cache["fetched"] = date.today().isoformat()
        save_cache(root, cache)

    if archive and cache.get("fetched"):
        path = archive_snapshot(root, cache)
        if path:
            print(f"Archived citation snapshot → {path.relative_to(root)}")
    return cache


def citation_series_from_cache(
    cache: dict,
    refereed: list[dict],
    *,
    exclusions: set[str] | None = None,
) -> tuple[dict[int, int], dict[int, int]]:
    exclusions = exclusions or set()
    papers = cache.get("papers") or {}
    by_pub_year: dict[int, int] = {}
    for pub in refereed:
        arxiv = (pub.get("arxiv") or "").strip()
        year = int(pub.get("year") or 0)
        if not arxiv or not year or arxiv in exclusions:
            continue
        count = int((papers.get(arxiv) or {}).get("citation_count") or 0)
        by_pub_year[year] = by_pub_year.get(year, 0) + count

    years_sorted = sorted(by_pub_year)
    stock: dict[int, int] = {}
    running = 0
    if years_sorted:
        min_y, max_y = min(years_sorted), max(years_sorted)
        for y in range(min_y, max_y + 1):
            running += by_pub_year.get(y, 0)
            stock[y] = running
    return by_pub_year, stock
