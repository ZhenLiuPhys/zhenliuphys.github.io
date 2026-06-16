#!/usr/bin/env python3
"""Normalize display fields in publications.yaml and talks.yaml."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from talk_fields import parse_talk_fields  # noqa: E402

LINK_RE = re.compile(r"\(\s*link\s*\)|\[\s*link\s*\]", re.I)
ARXIV_TAIL_RE = re.compile(
    r",?\s*(?:arXiv:)?\s*\d{4}\.\d{4,5}(?:v\d+)?\s*(?:\[[^\]]+\])?\s*(?:\(\d{4}\))?\s*$",
    re.I,
)
YEAR_TAIL_RE = re.compile(r"\s*\(\d{4}\)\s*$")
STATUS_RE = re.compile(r"\b(submitted|accepted|published|in press)\b", re.I)
JOURNAL_HINT_RE = re.compile(
    r"(Phys\.?\s*Rev\.?|PRL|PRD|JHEP|EPJC|Nature|Science|Chin\.?\s*Phys\.?|Nucl\.?\s*Phys\.?)",
    re.I,
)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = LINK_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.")
    return text


def simplify_venue(venue: str, arxiv: str) -> str:
    v = clean_text(venue)
    if arxiv:
        v = re.sub(rf",?\s*{re.escape(arxiv)}.*$", "", v, flags=re.I)
    v = ARXIV_TAIL_RE.sub("", v)
    v = YEAR_TAIL_RE.sub("", v).strip(" ,.")
    return v


def extract_status(venue: str) -> str:
    m = STATUS_RE.search(venue or "")
    return m.group(1).lower() if m else ""


def extract_journal(venue: str) -> str:
    v = simplify_venue(venue, "")
    if not v:
        return ""
    # Drop leading author list before journal name when comma-heavy.
    if JOURNAL_HINT_RE.search(v):
        m = JOURNAL_HINT_RE.search(v)
        if m:
            return v[m.start() :].strip(" ,.")
    # White-paper style: keep tail after first " , " chunk if short
    parts = [p.strip() for p in v.split(",") if p.strip()]
    if len(parts) >= 2 and len(parts[0]) < 60:
        return ", ".join(parts[1:])
    return v


def build_venue_display(pub: dict) -> str:
    venue = pub.get("venue") or ""
    arxiv = (pub.get("arxiv") or "").strip()
    journal = extract_journal(venue)
    status = extract_status(venue)
    parts: list[str] = []
    if journal:
        parts.append(journal)
    elif venue:
        parts.append(simplify_venue(venue, arxiv))
    if status and status not in (parts[0].lower() if parts else ""):
        parts.append(status)
    if not parts and arxiv:
        parts.append(f"arXiv:{arxiv}")
    return " · ".join(parts) if parts else ""


def simplify_talk_event(event: str) -> str:
    e = clean_text(event)
    e = re.sub(r"^,\s*", "", e)
    e = re.sub(
        r"^(?:\(scheduled\)\s*)?(?:invited|contributed)\s+(?:plenary\s+)?talk at\s+",
        "",
        e,
        flags=re.I,
    )
    e = re.sub(r"^(?:theory\s+seminar|seminar|colloquium),\s*", "", e, flags=re.I)
    e = re.sub(r",\s*May\.\s*202,\s*May\.\s*(\d{4})", r", May \1", e, flags=re.I)
    return e.strip(" ,.")


def is_placeholder_talk(title: str) -> bool:
    t = clean_text(title).lower()
    return t in {"tbd", "(scheduled) tbd"} or t.startswith("tbd ")


def normalize_publication(pub: dict) -> dict:
    pub["title"] = clean_text(pub.get("title", ""))
    pub["venue"] = clean_text(pub.get("venue", ""))
    arxiv = (pub.get("arxiv") or "").strip()
    pub["journal"] = extract_journal(pub.get("venue", ""))
    pub["status"] = extract_status(pub.get("venue", ""))
    pub["venue_display"] = build_venue_display(pub)
    if arxiv and pub["venue_display"] and arxiv in pub["venue_display"]:
        pub["venue_display"] = simplify_venue(pub["venue_display"], arxiv)
    if pub["status"] and pub["venue_display"]:
        # Avoid duplicate "submitted"/"accepted" where venue text already includes it.
        if re.search(rf"\b{re.escape(pub['status'])}\b", pub["venue_display"], re.I):
            pub["status"] = ""
    return pub


def normalize_talk(talk: dict) -> dict:
    talk["event"] = simplify_talk_event(clean_text(talk.get("event", "")))
    raw = clean_text(talk.get("raw_text", ""))
    raw = re.sub(r",\s*May\.\s*202,\s*May\.\s*(\d{4})", r", May \1", raw, flags=re.I)
    if raw:
        talk["raw_text"] = raw
    else:
        talk.pop("raw_text", None)
    return parse_talk_fields(talk)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean bibliography YAML display fields.")
    parser.add_argument("--pub", default="data/publications.yaml")
    parser.add_argument("--talks", default="data/talks.yaml")
    args = parser.parse_args()

    pub_path = Path(args.pub)
    talk_path = Path(args.talks)

    pubs = yaml.safe_load(pub_path.read_text(encoding="utf-8")) or []
    talks = yaml.safe_load(talk_path.read_text(encoding="utf-8")) or []

    pubs = [normalize_publication(p) for p in pubs]
    talks = [normalize_talk(t) for t in talks]

    pub_path.write_text(yaml.safe_dump(pubs, sort_keys=False, allow_unicode=True), encoding="utf-8")
    talk_path.write_text(yaml.safe_dump(talks, sort_keys=False, allow_unicode=True), encoding="utf-8")

    placeholders = sum(1 for t in talks if t.get("placeholder"))
    print(f"Cleaned {len(pubs)} publications -> {pub_path}")
    print(f"Cleaned {len(talks)} talks ({placeholders} placeholders flagged) -> {talk_path}")


if __name__ == "__main__":
    main()
