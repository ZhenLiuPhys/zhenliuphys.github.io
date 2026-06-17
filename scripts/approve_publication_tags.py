#!/usr/bin/env python3
"""Confirm provisional publication tags into the standard YAML."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publication_tag_workflow import (  # noqa: E402
    DEFAULT_APPROVALS_PATH,
    apply_approvals,
    list_pending_proposals,
    write_approvals_template,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review and confirm auto-drafted publication tags.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List publications with provisional tags awaiting confirmation.",
    )
    parser.add_argument(
        "--write-template",
        metavar="PATH",
        nargs="?",
        const=str(DEFAULT_APPROVALS_PATH),
        help="Write a fill-in JSON approvals file for pending proposals.",
    )
    parser.add_argument(
        "--approvals",
        metavar="PATH",
        help="Apply resolutions from an approvals JSON file.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent

    pub_path = root / "data/publications.yaml"
    publications = yaml.safe_load(pub_path.read_text(encoding="utf-8")) or [] if pub_path.exists() else []
    pending = list_pending_proposals(root, publications)

    if args.list or (not args.write_template and not args.approvals):
        if not pending:
            print("No provisional tags pending confirmation.")
            print("Confirmed standard: data/source/publication_tags.yaml")
            return
        print(f"Pending confirmation ({len(pending)}):")
        for item in pending:
            title = (item.get("title") or "")[:70]
            loc = item.get("arxiv") or item.get("id")
            tags = ", ".join(item.get("tags") or [])
            print(f"  {item['key']}  [{tags}]")
            print(f"    {title}")
        print()
        print("Next steps:")
        print("  1. python scripts/approve_publication_tags.py --write-template")
        print("  2. Edit backups/publication-tag-approvals.json (accept_proposed | custom | reject)")
        print("  3. python scripts/approve_publication_tags.py --approvals backups/publication-tag-approvals.json")
        print("  Or edit data/source/publication_tags.yaml directly for one-off changes.")
        if not args.list and not args.write_template and not args.approvals:
            raise SystemExit(1 if pending else 0)
        return

    if args.write_template:
        path = Path(args.write_template)
        if not pending:
            print("No pending proposals; template not written.")
            return
        write_approvals_template(path, pending)
        print(f"Wrote approval template ({len(pending)} items) to {path}")
        print("Set resolution per item, then run with --approvals.")
        return

    if args.approvals:
        path = Path(args.approvals)
        accepted, rejected, messages = apply_approvals(root, path)
        for msg in messages:
            print(msg)
        print(f"Done: {accepted} confirmed, {rejected} rejected.")
        if accepted:
            print("Re-run: python scripts/sync_publication_tags.py")


if __name__ == "__main__":
    main()
