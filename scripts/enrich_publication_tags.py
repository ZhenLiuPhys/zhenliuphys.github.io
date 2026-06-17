#!/usr/bin/env python3
"""Enrich confirmed publication tags toward 3–4 keywords per paper (min 2, max 6)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publication_tag_inference import refined_tags_for_publication, seed_from_selected, seed_from_themes
from publication_tag_workflow import load_confirmed, save_confirmed


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich confirmed publication_tags.yaml in place.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    pubs = yaml.safe_load((root / "data/publications.yaml").read_text(encoding="utf-8")) or []
    pub_by_arxiv = {p["arxiv"]: p for p in pubs if p.get("arxiv")}
    pub_by_id = {p["id"]: p for p in pubs if p.get("id")}

    confirmed_arxiv, confirmed_id = load_confirmed(root)
    selected_seeds = seed_from_selected(root)
    theme_seeds = seed_from_themes(root)

    changed = 0
    for arxiv, spec in list(confirmed_arxiv.items()):
        pub = pub_by_arxiv.get(arxiv, {"arxiv": arxiv, "title": "", "section": ""})
        old = list(spec)
        new = refined_tags_for_publication(
            pub,
            root,
            base_tags=set(old),
            selected_seeds=selected_seeds,
            theme_seeds=theme_seeds,
        )
        if new != old:
            changed += 1
            print(f"{arxiv}: {old} -> {new}")
            confirmed_arxiv[arxiv] = new

    for pub_id, spec in list(confirmed_id.items()):
        pub = pub_by_id.get(pub_id, {"id": pub_id, "title": "", "section": ""})
        old = list(spec)
        new = refined_tags_for_publication(
            pub,
            root,
            base_tags=set(old),
            selected_seeds=selected_seeds,
            theme_seeds=theme_seeds,
        )
        if new != old:
            changed += 1
            print(f"{pub_id}: {old} -> {new}")
            confirmed_id[pub_id] = new

    if args.dry_run:
        print(f"\nDry run: {changed} assignment(s) would change.")
        return

    if changed:
        save_confirmed(root, confirmed_arxiv, confirmed_id)
    print(f"Enriched {changed} assignment(s) in data/source/publication_tags.yaml")


if __name__ == "__main__":
    main()
