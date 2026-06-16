#!/usr/bin/env python3
"""Apply featured flags from selected_publications.yaml to data/publications.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from parse_cv_html import apply_featured_flags, load_yaml_list


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    pub_out = root / "data" / "publications.yaml"
    publications = load_yaml_list(pub_out)
    if not publications:
        raise SystemExit(f"No publications found in {pub_out}")

    apply_featured_flags(publications, root, pub_out)
    pub_out.write_text(
        yaml.safe_dump(publications, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    featured = sum(1 for p in publications if p.get("featured"))
    print(f"Updated {pub_out} ({featured} featured entries)")


if __name__ == "__main__":
    main()
