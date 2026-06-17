#!/usr/bin/env python3
"""Validate publication tag assignments."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publication_tag_workflow import list_pending_proposals, load_confirmed, load_proposals  # noqa: E402
from sync_publication_tags import (  # noqa: E402
    apply_publication_tags,
    valid_tag_ids,
)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    pub_path = root / "data/publications.yaml"
    publications = yaml.safe_load(pub_path.read_text(encoding="utf-8")) or []
    allowed = valid_tag_ids(root)
    confirmed_arxiv, confirmed_id = load_confirmed(root)
    proposal_arxiv, proposal_id = load_proposals(root)

    missing_confirmed = []
    for pub in publications:
        arxiv = (pub.get("arxiv") or "").strip()
        pub_id = (pub.get("id") or "").strip()
        if arxiv and arxiv not in confirmed_arxiv:
            missing_confirmed.append(f"{arxiv} {pub.get('title', '')[:50]}")
        elif not arxiv and pub_id not in confirmed_id:
            missing_confirmed.append(f"{pub_id} {pub.get('title', '')[:50]}")

    pending = list_pending_proposals(root, publications)

    pubs_copy = yaml.safe_load(pub_path.read_text(encoding="utf-8")) or []
    warnings = apply_publication_tags(pubs_copy, root)

    tag_counts: Counter[str] = Counter()
    bsm_only = []
    for pub in pubs_copy:
        tags = pub.get("tags") or []
        for t in tags:
            if t in allowed:
                tag_counts[t] += 1
        if tags == ["bsm"]:
            bsm_only.append((pub.get("arxiv") or pub.get("id"), pub.get("title", "")[:50]))

    print(f"Publications: {len(publications)}")
    print(f"Confirmed in publication_tags.yaml: {len(confirmed_arxiv) + len(confirmed_id)}")
    print(f"Provisional (awaiting confirmation): {len(pending)}")
    print(f"Not yet confirmed: {len(missing_confirmed)}")
    for line in missing_confirmed[:10]:
        print(f"  - {line}")
    if len(missing_confirmed) > 10:
        print(f"  ... and {len(missing_confirmed) - 10} more")

    if pending:
        print("\nPending proposals (site uses these until you confirm):")
        for item in pending[:10]:
            tags = ", ".join(item.get("tags") or [])
            print(f"  - {item['key']}: [{tags}] {(item.get('title') or '')[:50]}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")

    print("\nPer-tag counts (merged for site):")
    for tag_id in sorted(allowed, key=lambda x: (-tag_counts[x], x)):
        count = tag_counts[tag_id]
        flag = " (EMPTY)" if count == 0 else ""
        print(f"  {tag_id}: {count}{flag}")

    print(f"\nBSM-only papers: {len(bsm_only)}")
    for arxiv, title in bsm_only[:15]:
        print(f"  - {arxiv}: {title}")
    if len(bsm_only) > 15:
        print(f"  ... and {len(bsm_only) - 15} more")

    over_limit = [w for w in warnings if w.startswith("over limit")]
    unknown = [w for w in warnings if w.startswith("unknown tags")]
    untagged = [w for w in warnings if w.startswith("untagged:")]
    if over_limit:
        print("\nOver limit:")
        for w in over_limit:
            print(f"  {w}")
    if unknown:
        print("\nUnknown tags:")
        for w in unknown:
            print(f"  {w}")
    if untagged:
        print("\nUntagged (no confirmed or provisional tags):")
        for w in untagged:
            print(f"  {w}")

    ok = not untagged and not over_limit and not unknown
    if pending and ok:
        print("\nOK (provisional tags in use — confirm when ready)")
    elif ok:
        print("\nOK")
    else:
        print("\nISSUES FOUND")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
