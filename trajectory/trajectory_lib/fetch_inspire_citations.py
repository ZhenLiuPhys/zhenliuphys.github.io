"""Fetch and cache inSPIRE citation counts for refereed publications."""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import requests
import yaml

INSPIRE_API = "https://inspirehep.net/api/literature"
CACHE_VERSION = 1


def cache_path(root: Path) -> Path:
    return root / "trajectory/data/inspire_citations.yaml"


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


def ensure_citations(refereed: list[dict], root: Path, *, refresh: bool = False) -> dict:
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
