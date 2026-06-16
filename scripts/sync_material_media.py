from __future__ import annotations

from pathlib import Path
import shutil
import sys

# Local dev placeholders are ~4–6 KB; real photos are usually much larger.
LIKELY_PLACEHOLDER_MAX_BYTES = 12_000

ASSETS = (
    ("profilephoto", "static/images/profile/profilephoto.jpg"),
    ("researchsummary", "static/images/research/researchsummary.jpg"),
)

SOURCE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def resolve_source(material_dir: Path, stem: str) -> Path | None:
    for ext in SOURCE_EXTS:
        candidate = material_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        print(f"MISSING: {src.name} — copy from your main machine into Material/ (see Material/README.md)")
        return False
    size = src.stat().st_size
    if size <= LIKELY_PLACEHOLDER_MAX_BYTES:
        print(
            f"WARNING: {src.name} is only {size} bytes — likely a placeholder; "
            "replace with your real file when available."
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"copied: {src} -> {dst}")
    return True


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    missing = 0
    material = root / "Material"
    for stem, rel_dst in ASSETS:
        src = resolve_source(material, stem)
        dst = root / rel_dst
        if src is None or not copy_if_exists(src, dst):
            missing += 1
    if missing:
        print(f"\n{missing} Material image(s) missing; homepage uses a fallback until you add them.", file=sys.stderr)


if __name__ == "__main__":
    main()
