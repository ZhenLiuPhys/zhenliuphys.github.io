#!/usr/bin/env python3
"""Confirmed vs provisional publication tag workflow."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from publication_tag_inference import draft_tags_for_publication, seed_from_selected, seed_from_themes

CONFIRMED_PATH = Path("data/source/publication_tags.yaml")
PROPOSALS_PATH = Path("backups/publication-tag-proposals.yaml")
REVIEW_PATH = Path("backups/publication-tag-review.yaml")
DEFAULT_APPROVALS_PATH = Path("backups/publication-tag-approvals.json")

RESOLUTION_ACCEPT = "accept_proposed"
RESOLUTION_REJECT = "reject"
RESOLUTION_CUSTOM = "custom"
RESOLUTION_KEEP = "keep_confirmed"


def _parse_assignment_block(raw: dict) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    by_arxiv: dict[str, list[str]] = {}
    by_id: dict[str, list[str]] = {}
    for key, value in raw.items():
        if key == "by_id":
            if isinstance(value, dict):
                for pub_id, spec in value.items():
                    tags = spec.get("tags") if isinstance(spec, dict) else spec
                    if isinstance(tags, list):
                        by_id[str(pub_id)] = [str(t) for t in tags]
            continue
        if isinstance(value, dict) and "tags" in value:
            tags = value["tags"]
        elif isinstance(value, list):
            tags = value
        else:
            continue
        by_arxiv[str(key)] = [str(t) for t in tags]
    return by_arxiv, by_id


def load_assignment_file(path: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    if not path.exists():
        return {}, {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}, {}
    return _parse_assignment_block(raw)


def dump_assignment_file(
    path: Path,
    by_arxiv: dict[str, list[str]],
    by_id: dict[str, list[str]],
    header: str,
) -> None:
    out: dict = {k: {"tags": v} for k, v in sorted(by_arxiv.items())}
    if by_id:
        out["by_id"] = {k: {"tags": v} for k, v in sorted(by_id.items())}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_confirmed(root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    return load_assignment_file(root / CONFIRMED_PATH)


def load_proposals(root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    return load_assignment_file(root / PROPOSALS_PATH)


def save_proposals(root: Path, by_arxiv: dict[str, list[str]], by_id: dict[str, list[str]]) -> None:
    header = (
        "# Auto-drafted tags for new publications (local, gitignored).\n"
        "# Confirm with: python scripts/approve_publication_tags.py --approvals backups/publication-tag-approvals.json\n"
        "# Or edit data/source/publication_tags.yaml directly.\n"
    )
    dump_assignment_file(root / PROPOSALS_PATH, by_arxiv, by_id, header)


def save_confirmed(root: Path, by_arxiv: dict[str, list[str]], by_id: dict[str, list[str]]) -> None:
    header = (
        "# Confirmed publication tag assignments (arXiv-keyed; by_id for papers without arXiv).\n"
        "# This file is the standard — edits here are your approved tags.\n"
        "# New papers: auto-drafted to backups/publication-tag-proposals.yaml; confirm before merging here.\n"
        "# Workflow: python scripts/approve_publication_tags.py --list\n"
    )
    dump_assignment_file(root / CONFIRMED_PATH, by_arxiv, by_id, header)


def pub_lookup_keys(pub: dict) -> tuple[str | None, str | None]:
    arxiv = (pub.get("arxiv") or "").strip() or None
    pub_id = (pub.get("id") or "").strip() or None
    return arxiv, pub_id


def is_confirmed(
    arxiv: str | None,
    pub_id: str | None,
    confirmed_arxiv: dict[str, list[str]],
    confirmed_id: dict[str, list[str]],
) -> bool:
    if arxiv and arxiv in confirmed_arxiv:
        return True
    if not arxiv and pub_id and pub_id in confirmed_id:
        return True
    return False


def merged_tags_for_pub(
    pub: dict,
    confirmed_arxiv: dict[str, list[str]],
    confirmed_id: dict[str, list[str]],
    proposal_arxiv: dict[str, list[str]],
    proposal_id: dict[str, list[str]],
) -> tuple[list[str], str]:
    """Return (tags, source) where source is confirmed | provisional | missing."""
    arxiv, pub_id = pub_lookup_keys(pub)
    if arxiv and arxiv in confirmed_arxiv:
        return list(confirmed_arxiv[arxiv]), "confirmed"
    if not arxiv and pub_id and pub_id in confirmed_id:
        return list(confirmed_id[pub_id]), "confirmed"
    if arxiv and arxiv in proposal_arxiv:
        return list(proposal_arxiv[arxiv]), "provisional"
    if not arxiv and pub_id and pub_id in proposal_id:
        return list(proposal_id[pub_id]), "provisional"
    return [], "missing"


def propose_missing_publications(publications: list[dict], root: Path) -> int:
    """Draft tags for publications not yet confirmed. Never overwrites confirmed assignments."""
    confirmed_arxiv, confirmed_id = load_confirmed(root)
    proposal_arxiv, proposal_id = load_proposals(root)
    selected_seeds = seed_from_selected(root)
    theme_seeds = seed_from_themes(root)

    added = 0
    for pub in publications:
        arxiv, pub_id = pub_lookup_keys(pub)
        if is_confirmed(arxiv, pub_id, confirmed_arxiv, confirmed_id):
            continue
        if arxiv and arxiv in proposal_arxiv:
            continue
        if not arxiv and pub_id and pub_id in proposal_id:
            continue

        tags = draft_tags_for_publication(
            pub,
            root,
            selected_seeds=selected_seeds,
            theme_seeds=theme_seeds,
        )
        if arxiv:
            proposal_arxiv[arxiv] = tags
            added += 1
        elif pub_id:
            proposal_id[pub_id] = tags
            added += 1

    if added:
        save_proposals(root, proposal_arxiv, proposal_id)
    return added


def list_pending_proposals(root: Path, publications: list[dict] | None = None) -> list[dict]:
    confirmed_arxiv, confirmed_id = load_confirmed(root)
    proposal_arxiv, proposal_id = load_proposals(root)
    pending: list[dict] = []

    pub_by_arxiv: dict[str, dict] = {}
    pub_by_id: dict[str, dict] = {}
    if publications:
        for pub in publications:
            arxiv, pub_id = pub_lookup_keys(pub)
            if arxiv:
                pub_by_arxiv[arxiv] = pub
            if pub_id:
                pub_by_id[pub_id] = pub

    for arxiv, tags in sorted(proposal_arxiv.items()):
        if arxiv in confirmed_arxiv:
            continue
        pub = pub_by_arxiv.get(arxiv, {})
        pending.append(
            {
                "key": f"arxiv:{arxiv}",
                "arxiv": arxiv,
                "id": pub.get("id"),
                "title": pub.get("title") or "",
                "section": pub.get("section") or "",
                "tags": tags,
            }
        )

    for pub_id, tags in sorted(proposal_id.items()):
        if pub_id in confirmed_id:
            continue
        pub = pub_by_id.get(pub_id, {})
        pending.append(
            {
                "key": f"id:{pub_id}",
                "arxiv": pub.get("arxiv"),
                "id": pub_id,
                "title": pub.get("title") or "",
                "section": pub.get("section") or "",
                "tags": tags,
            }
        )

    return pending


def write_heuristic_review(root: Path, publications: list[dict]) -> int:
    """Informational drift report when heuristics differ from confirmed tags (never auto-applied)."""
    confirmed_arxiv, confirmed_id = load_confirmed(root)
    selected_seeds = seed_from_selected(root)
    theme_seeds = seed_from_themes(root)
    drift: dict = {}

    for pub in publications:
        arxiv, pub_id = pub_lookup_keys(pub)
        confirmed: list[str] | None = None
        key: str | None = None
        if arxiv and arxiv in confirmed_arxiv:
            confirmed = confirmed_arxiv[arxiv]
            key = arxiv
        elif not arxiv and pub_id and pub_id in confirmed_id:
            confirmed = confirmed_id[pub_id]
            key = pub_id
        if not confirmed or not key:
            continue

        suggested = draft_tags_for_publication(
            pub,
            root,
            selected_seeds=selected_seeds,
            theme_seeds=theme_seeds,
        )
        if sorted(confirmed) != sorted(suggested):
            drift[key] = {
                "title": (pub.get("title") or "")[:80],
                "confirmed": confirmed,
                "suggested": suggested,
            }

    if drift:
        header = (
            "# Heuristic suggestions that differ from your confirmed tags (informational only).\n"
            "# Confirmed tags in data/source/publication_tags.yaml are never auto-changed.\n"
        )
        path = root / REVIEW_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(header + yaml.safe_dump(drift, sort_keys=True, allow_unicode=True), encoding="utf-8")
    elif (root / REVIEW_PATH).exists():
        (root / REVIEW_PATH).unlink()

    return len(drift)


def proposal_key(item: dict) -> str:
    if item.get("key"):
        return str(item["key"])
    if item.get("arxiv"):
        return f"arxiv:{item['arxiv']}"
    if item.get("id"):
        return f"id:{item['id']}"
    return ""


def load_approvals(path: Path | None) -> dict[str, dict]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("approvals") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return {}
    out: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if key:
            out[key] = item
    return out


def write_approvals_template(path: Path, pending: list[dict]) -> None:
    template = {
        "approvals": [
            {
                "key": item["key"],
                "resolution": RESOLUTION_ACCEPT,
                "tags": item["tags"],
                "title": (item.get("title") or "")[:80],
                "note": (
                    "accept_proposed — merge proposed tags into publication_tags.yaml; "
                    "custom — set tags explicitly; reject — drop proposal (paper stays untagged until you edit YAML)."
                ),
            }
            for item in pending
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_approvals(root: Path, approvals_path: Path) -> tuple[int, int, list[str]]:
    """Merge accepted/custom tags into confirmed YAML; prune proposals. Returns (accepted, rejected, messages)."""
    pending = {item["key"]: item for item in list_pending_proposals(root)}
    approvals = load_approvals(approvals_path)
    if not approvals:
        return 0, 0, ["No approvals loaded."]

    confirmed_arxiv, confirmed_id = load_confirmed(root)
    proposal_arxiv, proposal_id = load_proposals(root)
    accepted = 0
    rejected = 0
    messages: list[str] = []

    for key, item in approvals.items():
        resolution = str(item.get("resolution") or "").strip().lower()
        pending_item = pending.get(key)
        if not pending_item and resolution not in {RESOLUTION_KEEP, RESOLUTION_CUSTOM}:
            messages.append(f"skip unknown key: {key}")
            continue

        arxiv = pending_item.get("arxiv") if pending_item else None
        pub_id = pending_item.get("id") if pending_item else None
        if key.startswith("arxiv:"):
            arxiv = key.split(":", 1)[1]
        elif key.startswith("id:"):
            pub_id = key.split(":", 1)[1]

        if resolution == RESOLUTION_REJECT:
            if arxiv and arxiv in proposal_arxiv:
                del proposal_arxiv[arxiv]
            if pub_id and pub_id in proposal_id:
                del proposal_id[pub_id]
            rejected += 1
            messages.append(f"rejected: {key}")
            continue

        if resolution == RESOLUTION_KEEP:
            messages.append(f"kept confirmed (no change): {key}")
            continue

        tags: list[str] | None = None
        if resolution == RESOLUTION_CUSTOM:
            raw = item.get("tags")
            if isinstance(raw, list) and raw:
                tags = [str(t) for t in raw]
        elif resolution == RESOLUTION_ACCEPT:
            tags = list(pending_item.get("tags") or []) if pending_item else None
            custom = item.get("tags")
            if isinstance(custom, list) and custom:
                tags = [str(t) for t in custom]

        if not tags:
            messages.append(f"skip {key}: no tags for resolution {resolution}")
            continue

        if arxiv:
            confirmed_arxiv[arxiv] = tags
            proposal_arxiv.pop(arxiv, None)
        elif pub_id:
            confirmed_id[pub_id] = tags
            proposal_id.pop(pub_id, None)
        else:
            messages.append(f"skip {key}: missing arxiv/id")
            continue

        accepted += 1
        messages.append(f"confirmed: {key} → {tags}")

    save_confirmed(root, confirmed_arxiv, confirmed_id)
    save_proposals(root, proposal_arxiv, proposal_id)
    return accepted, rejected, messages
