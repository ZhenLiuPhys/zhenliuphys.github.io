#!/usr/bin/env python3
"""Heuristic publication tag inference (draft proposals only)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

TOPIC_MAP = {
    "higgs": ["higgs"],
    "muon_colliders": ["muon-collider"],
    "amplitudes": ["amplitudes"],
    "axions": ["axions"],
    "dark_sector": ["dark-sector"],
    "bsm": ["bsm"],
}

THEME_MAP = {
    "muon-colliders": ["muon-collider"],
    "dark-sector": ["dark-sector"],
    "amplitudes-bsm": ["amplitudes", "bsm"],
}

TAG_ORDER = [
    "higgs",
    "standard-model",
    "bsm",
    "supersymmetry",
    "dark-sector",
    "axions",
    "neutrinos",
    "neutron-stars",
    "long-lived-particles",
    "forward-physics",
    "phase-transition",
    "lhc",
    "muon-collider",
    "cepc-fcc",
    "beamdump",
    "qis",
    "quantum-sensing",
    "amplitudes",
    "eft",
    "ai-ml",
]

NARROW_TAGS = {
    "axions",
    "long-lived-particles",
    "supersymmetry",
    "neutron-stars",
    "forward-physics",
    "phase-transition",
}

ARXIV_OVERRIDES: dict[str, list[str]] = {
    "2605.08433": ["eft", "higgs", "bsm"],
    "2605.13964": ["dark-sector", "forward-physics", "lhc"],
    "2604.13156": ["standard-model", "lhc"],
    "2604.14284": ["higgs", "bsm", "muon-collider"],
    "2602.17582": ["ai-ml", "bsm"],
    "2512.04336": ["amplitudes", "lhc", "bsm"],
    "2510.02427": ["quantum-sensing", "dark-sector"],
    "2509.10605": ["axions", "muon-collider"],
    "2508.04961": ["neutron-stars", "dark-sector"],
    "2506.02106": ["amplitudes"],
    "2403.15538": ["amplitudes", "bsm"],
    "2301.11512": ["quantum-sensing", "dark-sector"],
    "2207.08448": ["axions", "dark-sector"],
    "2009.11287": ["dark-sector", "muon-collider"],
    "1911.07996": ["dark-sector", "beamdump"],
    "1908.04797": ["quantum-sensing", "dark-sector"],
    "1805.05957": ["long-lived-particles", "lhc", "bsm"],
    "1704.08259": ["higgs", "lhc", "standard-model"],
    "1612.09284": ["higgs", "cepc-fcc"],
    "1608.07282": ["bsm", "lhc", "higgs"],
    "1503.05923": ["supersymmetry", "long-lived-particles", "lhc"],
    "1406.1181": ["supersymmetry", "dark-sector", "bsm"],
    "1311.7155": ["higgs", "cepc-fcc"],
    "1010.4309": ["bsm", "lhc"],
}

ID_OVERRIDES: dict[str, list[str]] = {
    "pub-l2-003-a-cool-route-to-the-higgs-boson-and-beyond-the-cool-copper-collider": [
        "cepc-fcc",
        "higgs",
    ],
    "pub-l3-035-future-circular-collider-vol-4-the-high-energy-lhc-he-lhc": [
        "cepc-fcc",
        "lhc",
        "bsm",
    ],
    "pub-l3-034-future-circular-collider-vol-3-the-hadron-collider-fcc-hh": [
        "cepc-fcc",
        "lhc",
        "bsm",
    ],
    "pub-l3-033-future-circular-collider-vol-2-the-lepton-collider-fcc-ee": [
        "cepc-fcc",
        "higgs",
        "bsm",
    ],
    "pub-l3-032-future-circular-collider-vol-1-physics-opportunities": [
        "cepc-fcc",
        "bsm",
    ],
    "pub-l2-018-probing-the-higgs-with-angular-observables-at-future-e-e-colliders": [
        "higgs",
        "cepc-fcc",
    ],
    "pub-l2-019-cepc-sppc-preliminary-conceptual-design-report-volume-i-physics-and-detector": [
        "cepc-fcc",
        "bsm",
    ],
    "pub-l2-020-beyond-standard-model-physics-at-current-and-future-colliders": [
        "bsm",
        "lhc",
        "cepc-fcc",
    ],
}


def load_yaml(path: Path):
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def add_tags(tags: set[str], *new: str) -> None:
    tags.update(t for t in new if t)


def infer_tags(title: str, section: str) -> set[str]:
    t = title.lower()
    tags: set[str] = set()
    is_white = section != "refereed_journals"

    if re.search(r"\bsmeft\b|\bheft\b|effective field|electroweak restoration", t):
        add_tags(tags, "eft")
    if re.search(r"amplitude|positivity|on-shell|recursion|helicity|momentum shift", t):
        add_tags(tags, "amplitudes")
    if re.search(r"ai-native|machine learning|\bml\b|artificial intelligence", t):
        add_tags(tags, "ai-ml")
    if re.search(r"quantum information|\bqis\b|quantum comput", t):
        add_tags(tags, "qis")
    if re.search(r"quantum sensor|mechanical sensor|dark srf|\bsrf\b|ultralow.threshold", t):
        add_tags(tags, "quantum-sensing")

    if re.search(r"neutron star", t):
        add_tags(tags, "neutron-stars", "dark-sector")
    if re.search(r"\baxion", t):
        add_tags(tags, "axions")
    if re.search(r"neutrino", t):
        add_tags(tags, "neutrinos")
    if re.search(r"long.lived|displaced|mathusla|superpartner|gluino|squark|electroweakino", t):
        add_tags(tags, "long-lived-particles")
    if re.search(r"forward|shower|millicharged", t):
        add_tags(tags, "forward-physics")
    if re.search(r"phase transition", t):
        add_tags(tags, "phase-transition")
    if re.search(r"supersymmetr|neutralino|wino|higgsino|sparticle|\bsusy\b", t):
        add_tags(tags, "supersymmetry")
    if re.search(r"\bhiggs\b|125 gev", t):
        add_tags(tags, "higgs")
    if re.search(r"dark photon|dark matter|dark sector|hidden sector|wimp|millicharged|dark srf", t):
        add_tags(tags, "dark-sector")

    if re.search(r"muon collider|mucol|\bimcc\b", t):
        add_tags(tags, "muon-collider")
    if re.search(r"\bcepc\b|\bfcc\b|\bilc\b|cool copper|future circular|lepton collider|e\+e-|e\^\+e", t):
        add_tags(tags, "cepc-fcc")
    if re.search(r"\blhc\b|large hadron", t):
        add_tags(tags, "lhc")
    if re.search(r"beam dump|beamdump|fixed.target|pip-ii|jefferson lab", t):
        add_tags(tags, "beamdump")

    if re.search(
        r"beyond standard model|\bbsm\b|new physics|exotic|resonance|extra dimension|"
        r"technicolor|composite|z'|w'|heavy scalar|top partner",
        t,
    ):
        add_tags(tags, "bsm")

    if re.search(r"standard model|gg->|radiative decay z", t) and "beyond standard model" not in t:
        if not tags.intersection({"bsm", "supersymmetry", "axions", "dark-sector"}):
            add_tags(tags, "standard-model")

    if is_white and re.search(r"white paper|technical design|conceptual design|milestone|snowmass|community", t):
        if not tags:
            add_tags(tags, "bsm")

    if not tags:
        add_tags(tags, "bsm")

    if tags & NARROW_TAGS and "bsm" in tags and len(tags) > 2:
        tags.discard("bsm")

    return tags


def seed_from_selected(root: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in load_yaml(root / "data/source/selected_publications.yaml"):
        arxiv = (row.get("arxiv") or "").strip()
        if not arxiv:
            continue
        tags: set[str] = set()
        topic = row.get("topic") or ""
        if topic in TOPIC_MAP:
            tags.update(TOPIC_MAP[topic])
        for theme in row.get("theme_ids") or []:
            tags.update(THEME_MAP.get(theme, []))
        if tags:
            out[arxiv] = sorted(tags)
    return out


def seed_from_themes(root: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for theme in load_yaml(root / "data/source/research_themes.yaml"):
        theme_id = theme.get("id") or ""
        extra = THEME_MAP.get(theme_id, [])
        for arxiv in theme.get("papers") or []:
            arxiv = str(arxiv).strip()
            if not arxiv:
                continue
            cur = set(out.get(arxiv, []))
            cur.update(extra)
            out[arxiv] = sorted(cur)
    return out


def order_tags(tags: set[str], section: str) -> list[str]:
    limit = 4 if section != "refereed_journals" else 5
    ordered = [x for x in TAG_ORDER if x in tags][:limit]
    return ordered or ["bsm"]


def draft_tags_for_publication(
    pub: dict,
    root: Path,
    selected_seeds: dict[str, list[str]] | None = None,
    theme_seeds: dict[str, list[str]] | None = None,
) -> list[str]:
    arxiv = (pub.get("arxiv") or "").strip()
    pub_id = (pub.get("id") or "").strip()
    section = pub.get("section") or ""
    title = pub.get("title") or ""

    if arxiv and arxiv in ARXIV_OVERRIDES:
        return list(ARXIV_OVERRIDES[arxiv])
    if pub_id and pub_id in ID_OVERRIDES:
        return list(ID_OVERRIDES[pub_id])

    selected_seeds = selected_seeds if selected_seeds is not None else seed_from_selected(root)
    theme_seeds = theme_seeds if theme_seeds is not None else seed_from_themes(root)

    tags: set[str] = set()
    if arxiv:
        tags.update(selected_seeds.get(arxiv, []))
        tags.update(theme_seeds.get(arxiv, []))
    tags.update(infer_tags(title, section))
    return order_tags(tags, section)
