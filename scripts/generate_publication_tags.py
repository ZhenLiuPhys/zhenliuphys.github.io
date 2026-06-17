#!/usr/bin/env python3
"""Draft publication_tags.yaml from titles + curation seeds (bulk reset — use with care)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml

from publication_tag_inference import draft_tags_for_publication, seed_from_selected, seed_from_themes
from publication_tag_workflow import save_confirmed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-generate confirmed tags (overwrites publication_tags.yaml).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Required to overwrite your confirmed publication_tags.yaml.",
    )
    args = parser.parse_args()

    if not args.force:
        print(
            "Refusing to overwrite confirmed tags without --force.\n"
            "Normal workflow:\n"
            "  - New papers: auto-drafted on prepare_site / CV parse\n"
            "  - Confirm: python scripts/approve_publication_tags.py --list\n"
            "  - Edit standard: data/source/publication_tags.yaml\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    pubs = yaml.safe_load((ROOT / "data/publications.yaml").read_text(encoding="utf-8")) or []
    selected_seeds = seed_from_selected(ROOT)
    theme_seeds = seed_from_themes(ROOT)

    by_arxiv: dict[str, list[str]] = {}
    by_id: dict[str, list[str]] = {}

    for pub in pubs:
        arxiv = (pub.get("arxiv") or "").strip()
        pub_id = (pub.get("id") or "").strip()
        tags = draft_tags_for_publication(
            pub,
            ROOT,
            selected_seeds=selected_seeds,
            theme_seeds=theme_seeds,
        )
        if arxiv:
            by_arxiv[arxiv] = tags
        elif pub_id:
            by_id[pub_id] = tags

    save_confirmed(ROOT, by_arxiv, by_id)
    print(f"Wrote confirmed tags ({len(by_arxiv)} arXiv, {len(by_id)} by_id)")


if __name__ == "__main__":
    main()
