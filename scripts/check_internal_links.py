#!/usr/bin/env python3
"""Fail if built HTML contains broken same-site hrefs (run after hugo build)."""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path


def normalize_href_path(path: str, base_path: str) -> str:
    """Strip GitHub Pages project prefix (e.g. /homepage) before resolving files."""
    prefix = base_path.rstrip("/")
    if prefix and (path == prefix or path.startswith(prefix + "/")):
        path = path[len(prefix) :] or "/"
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check built HTML for broken internal hrefs.")
    parser.add_argument(
        "--base-path",
        default="",
        help="URL path prefix to strip from hrefs (e.g. /homepage for project Pages).",
    )
    args = parser.parse_args()
    base_path = args.base_path.rstrip("/")

    root = Path("public")
    if not root.is_dir():
        print("error: public/ not found — run hugo --minify first", file=sys.stderr)
        return 1

    broken: set[tuple[str, str]] = set()
    checked = 0
    for html in root.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="ignore")
        for href in re.findall(r'href=(?:"([^"#]+)"|\'([^\'#]+)\'|([^"\'#\s>]+))', text):
            href = href[0] or href[1] or href[2]
            if not href:
                continue
            if href.startswith(("http://", "https://", "mailto:", "tel:", "//")):
                continue
            path = urllib.parse.unquote(href.split("?")[0])
            if not path.startswith("/"):
                continue
            path = normalize_href_path(path, base_path)
            # Hugo Pipes may emit hashed asset URLs; skip stylesheet paths.
            if path.startswith("/css/") or path.startswith("/assets/"):
                continue
            checked += 1
            target = root / path.lstrip("/")
            if path.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                broken.add((str(html.relative_to(root)), href))

    if broken:
        print(f"Broken internal links ({len(broken)}):")
        for page, href in sorted(broken)[:50]:
            print(f"  {href}  (from {page})")
        if len(broken) > 50:
            print(f"  ... and {len(broken) - 50} more")
        return 1

    print(f"OK: {checked} internal hrefs checked, none broken.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
