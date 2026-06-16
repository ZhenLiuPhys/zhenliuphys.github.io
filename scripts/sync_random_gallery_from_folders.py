#!/usr/bin/env python3
"""
Generate data/photos.yaml from static/images/photos/.

Photos: optional short caption via filename — name__My caption here.jpg
Manual fields in data/photos.yaml (caption, year, location, credit, link) are preserved on re-sync.

Figures: edit data/source/figures.yaml by hand (long captions, credit, links).
  Place image files in static/images/plots/ and reference them there.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

import yaml


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


def is_image(path: Path) -> bool:
    if not path.is_file() or path.name.startswith("."):
        return False
    if path.name.lower().startswith("placeholder"):
        return False
    return path.suffix.lower() in IMAGE_EXTS


def caption_from_filename(path: Path) -> str:
    stem = path.stem
    if "__" not in stem:
        return ""
    _prefix, cap = stem.split("__", 1)
    cap = cap.strip()
    cap = re.sub(r"\s+", " ", cap)
    return cap


def build_entries(folder: Path, url_prefix: str) -> list[dict[str, str]]:
    files = sorted([p for p in folder.iterdir() if is_image(p)], key=lambda p: p.name.lower())
    entries: list[dict[str, str]] = []
    for p in files:
        entries.append(
            {
                "file": f"{url_prefix}/{p.name}",
                "caption": caption_from_filename(p),
                "year": "",
                "location": "",
                "credit": "",
                "link": "",
            }
        )
    return entries


def load_existing_photos(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        return {}
    by_file: dict[str, dict[str, str]] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        file_key = row.get("file")
        if file_key:
            by_file[str(file_key)] = row
    return by_file


def merge_photos(existing_by_file: dict[str, dict[str, str]], fresh: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    for entry in fresh:
        file_key = entry["file"]
        old = existing_by_file.get(file_key, {})
        row = {
            "file": file_key,
            "caption": str(old.get("caption") or entry.get("caption") or ""),
            "year": str(old.get("year") or ""),
            "location": str(old.get("location") or ""),
            "credit": str(old.get("credit") or ""),
            "link": str(old.get("link") or ""),
        }
        merged.append(row)
    return merged


def write_yaml(path: Path, data: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    photos_dir = root / "static" / "images" / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    (root / "static" / "images" / "plots").mkdir(parents=True, exist_ok=True)

    photos_yaml = root / "data" / "photos.yaml"
    existing = load_existing_photos(photos_yaml)
    fresh = build_entries(photos_dir, "/images/photos")
    photos = merge_photos(existing, fresh)
    write_yaml(photos_yaml, photos)

    print(f"Updated data/photos.yaml ({len(photos)} items)")
    figures_path = root / "data" / "source" / "figures.yaml"
    if figures_path.exists():
        figs = yaml.safe_load(figures_path.read_text(encoding="utf-8")) or []
        n = len(figs) if isinstance(figs, list) else 0
        print(f"Figures: {n} entries in data/source/figures.yaml (edit manually)")
    else:
        print("NOTE: create data/source/figures.yaml for curated figure captions", file=sys.stderr)
    if not photos:
        print("WARNING: no images found in static/images/photos/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
