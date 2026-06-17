#!/usr/bin/env python3
"""Merge confirmed + provisional publication tags into data/publications.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publication_tag_workflow import (  # noqa: E402
    load_confirmed,
    load_proposals,
    merged_tags_for_pub,
    propose_missing_publications,
    write_heuristic_review,
)

VOCAB_PATH = Path("data/source/publication_tag_vocab.yaml")
PUB_PATH = Path("data/publications.yaml")

REFEREED_SECTIONS = {"refereed_journals"}
MAX_TAGS_REFEREED = 5
MAX_TAGS_OTHER = 4


def load_vocab(root: Path) -> list[dict]:
    path = root / VOCAB_PATH
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [row for row in data if isinstance(row, dict) and row.get("id")]


def valid_tag_ids(root: Path) -> set[str]:
    return {row["id"] for row in load_vocab(root)}


def load_assignments(root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Confirmed assignments only (for validators that check the standard file)."""
    return load_confirmed(root)


def max_tags_for_section(section: str) -> int:
    return MAX_TAGS_REFEREED if section in REFEREED_SECTIONS else MAX_TAGS_OTHER


def apply_publication_tags(publications: list[dict], root: Path) -> list[str]:
    """Return warning messages. Auto-proposes tags for new papers; never overwrites confirmed."""
    warnings: list[str] = []
    allowed = valid_tag_ids(root)

    added = propose_missing_publications(publications, root)
    if added:
        warnings.append(f"provisional: auto-drafted tags for {added} new publication(s) — confirm to make standard")

    drift = write_heuristic_review(root, publications)
    if drift:
        warnings.append(
            f"review: heuristics differ from confirmed tags on {drift} paper(s) — see backups/publication-tag-review.yaml"
        )

    confirmed_arxiv, confirmed_id = load_confirmed(root)
    proposal_arxiv, proposal_id = load_proposals(root)
    provisional_count = 0

    for pub in publications:
        arxiv = (pub.get("arxiv") or "").strip()
        pub_id = (pub.get("id") or "").strip()
        section = pub.get("section") or ""
        title = pub.get("title") or pub_id

        tags, source = merged_tags_for_pub(
            pub,
            confirmed_arxiv,
            confirmed_id,
            proposal_arxiv,
            proposal_id,
        )
        if source == "missing":
            warnings.append(f"untagged: {arxiv or pub_id} — {title[:60]}")
        elif source == "provisional":
            provisional_count += 1

        unknown = [t for t in tags if t not in allowed]
        if unknown:
            warnings.append(f"unknown tags {unknown} on {arxiv or pub_id}")

        tags = [t for t in tags if t in allowed]
        limit = max_tags_for_section(section)
        if len(tags) > limit:
            warnings.append(
                f"over limit ({len(tags)}>{limit}): {arxiv or pub_id} — {title[:50]}"
            )
            tags = tags[:limit]

        pub["tags"] = tags

    if provisional_count:
        warnings.append(
            f"pending confirmation: {provisional_count} publication(s) use provisional tags "
            f"(python scripts/approve_publication_tags.py --list)"
        )

    return warnings


def sync_publication_tags(root: Path | None = None, pub_out: Path | None = None) -> list[str]:
    root = root or Path(__file__).resolve().parent.parent
    pub_out = pub_out or root / PUB_PATH
    publications = yaml.safe_load(pub_out.read_text(encoding="utf-8")) or []
    if not publications:
        return [f"No publications in {pub_out}"]

    warnings = apply_publication_tags(publications, root)
    pub_out.write_text(
        yaml.safe_dump(publications, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    tagged = sum(1 for p in publications if p.get("tags"))
    confirmed_arxiv, confirmed_id = load_confirmed(root)
    confirmed_n = len(confirmed_arxiv) + len(confirmed_id)
    print(f"Updated {pub_out} ({tagged}/{len(publications)} tagged, {confirmed_n} confirmed in YAML)")
    for msg in warnings:
        print(f"WARNING: {msg}", file=sys.stderr)
    return warnings


def main() -> None:
    warnings = sync_publication_tags()
    if any(w.startswith("untagged:") for w in warnings):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
