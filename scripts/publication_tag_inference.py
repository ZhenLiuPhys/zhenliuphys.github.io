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

MIN_TAGS = 2
TARGET_TAGS = 4
MAX_TAGS_REFEREED = 6
MAX_TAGS_OTHER = 5

NARROW_TAGS = {
    "axions",
    "long-lived-particles",
    "supersymmetry",
    "neutron-stars",
    "forward-physics",
    "phase-transition",
}

COMPANION_TAGS: dict[str, list[str]] = {
    "axions": ["dark-sector"],
    "long-lived-particles": ["bsm", "lhc"],
    "supersymmetry": ["dark-sector", "bsm"],
    "phase-transition": ["higgs", "bsm"],
    "neutrinos": ["bsm"],
    "neutron-stars": ["dark-sector", "bsm"],
    "forward-physics": ["dark-sector", "lhc"],
    "quantum-sensing": ["dark-sector"],
    "amplitudes": ["bsm"],
    "eft": ["bsm"],
    "ai-ml": ["bsm"],
    "qis": ["bsm"],
    "higgs": ["bsm"],
}

ARXIV_OVERRIDES: dict[str, list[str]] = {
    "2605.08433": ["eft", "higgs", "bsm"],
    "2605.13964": ["dark-sector", "forward-physics", "lhc"],
    "2604.13156": ["standard-model", "lhc"],
    "2604.14284": ["higgs", "bsm", "muon-collider"],
    "2602.17582": ["ai-ml", "bsm"],
    "2512.04336": ["amplitudes", "lhc", "bsm"],
    "2510.02427": ["quantum-sensing", "dark-sector"],
    "2509.10605": ["axions", "muon-collider", "bsm"],
    "2508.04961": ["neutron-stars", "dark-sector", "bsm"],
    "2506.02106": ["amplitudes", "bsm"],
    "2403.15538": ["amplitudes", "bsm"],
    "2306.00079": ["bsm", "amplitudes", "lhc"],
    "2301.11512": ["quantum-sensing", "dark-sector"],
    "2207.08448": ["axions", "dark-sector", "beamdump"],
    "2103.14043": ["bsm", "muon-collider", "forward-physics"],
    "2009.11287": ["dark-sector", "muon-collider", "bsm"],
    "2011.05995": ["axions", "dark-sector", "beamdump"],
    "1911.07996": ["dark-sector", "beamdump", "forward-physics"],
    "1911.10206": ["phase-transition", "higgs", "bsm"],
    "1908.04797": ["quantum-sensing", "dark-sector", "bsm"],
    "1806.07396": ["long-lived-particles", "lhc", "bsm", "forward-physics"],
    "1805.05957": ["long-lived-particles", "lhc", "bsm"],
    "1704.08259": ["higgs", "lhc", "standard-model"],
    "1612.09284": ["higgs", "cepc-fcc", "bsm"],
    "1608.07282": ["bsm", "lhc", "higgs"],
    "1506.06736": ["bsm", "lhc", "eft"],
    "1507.01923": ["higgs", "bsm", "lhc", "eft"],
    "1503.05923": ["supersymmetry", "long-lived-particles", "lhc"],
    "1406.1181": ["supersymmetry", "dark-sector", "bsm"],
    "1311.7155": ["higgs", "cepc-fcc", "bsm"],
    "1010.4309": ["bsm", "lhc", "amplitudes"],
}

ID_OVERRIDES: dict[str, list[str]] = {
    "pub-l2-003-a-cool-route-to-the-higgs-boson-and-beyond-the-cool-copper-collider": [
        "cepc-fcc",
        "higgs",
        "bsm",
    ],
    "pub-l3-035-future-circular-collider-vol-4-the-high-energy-lhc-he-lhc": [
        "cepc-fcc",
        "lhc",
        "bsm",
        "higgs",
    ],
    "pub-l3-034-future-circular-collider-vol-3-the-hadron-collider-fcc-hh": [
        "cepc-fcc",
        "lhc",
        "bsm",
        "higgs",
    ],
    "pub-l3-033-future-circular-collider-vol-2-the-lepton-collider-fcc-ee": [
        "cepc-fcc",
        "higgs",
        "bsm",
    ],
    "pub-l3-032-future-circular-collider-vol-1-physics-opportunities": [
        "cepc-fcc",
        "bsm",
        "higgs",
    ],
    "pub-l2-018-probing-the-higgs-with-angular-observables-at-future-e-e-colliders": [
        "higgs",
        "cepc-fcc",
        "bsm",
    ],
    "pub-l2-019-cepc-sppc-preliminary-conceptual-design-report-volume-i-physics-and-detector": [
        "cepc-fcc",
        "bsm",
        "higgs",
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


def pub_text(pub: dict) -> str:
    parts = [
        pub.get("title") or "",
        pub.get("venue") or "",
        pub.get("venue_display") or "",
        pub.get("journal") or "",
    ]
    return " ".join(p for p in parts if p)


def add_tags(tags: set[str], *new: str) -> None:
    tags.update(t for t in new if t)


def infer_tags(title: str, section: str, text: str = "") -> set[str]:
    t = f"{title} {text}".lower()
    tags: set[str] = set()
    is_white = section != "refereed_journals"

    if re.search(r"\bsmeft\b|\bheft\b|effective field|electroweak restoration|wilson coefficient", t):
        add_tags(tags, "eft")
    if re.search(
        r"amplitude|positivity|on-shell|recursion|helicity|momentum shift|constructib|compton",
        t,
    ):
        add_tags(tags, "amplitudes")
    if re.search(r"ai-native|machine learning|\bml\b|artificial intelligence", t):
        add_tags(tags, "ai-ml")
    if re.search(r"quantum information|\bqis\b|quantum comput", t):
        add_tags(tags, "qis")
    if re.search(
        r"quantum sensor|mechanical sensor|dark srf|\bsrf\b|ultralow.threshold|optomechan",
        t,
    ):
        add_tags(tags, "quantum-sensing")

    if re.search(r"neutron star", t):
        add_tags(tags, "neutron-stars", "dark-sector")
    if re.search(r"\baxion", t):
        add_tags(tags, "axions")
    if re.search(r"neutrino", t):
        add_tags(tags, "neutrinos")
    if re.search(
        r"long.lived|displaced|mathusla|superpartner|gluino|squark|electroweakino|soft displaced",
        t,
    ):
        add_tags(tags, "long-lived-particles")
    if re.search(r"forward|shower|millicharged|smasher", t):
        add_tags(tags, "forward-physics")
    if re.search(r"phase transition", t):
        add_tags(tags, "phase-transition")
    if re.search(r"supersymmetr|neutralino|wino|higgsino|sparticle|\bsusy\b|\bnmssm\b|\bmssm\b", t):
        add_tags(tags, "supersymmetry")
    if re.search(r"\bhiggs\b|125 gev|di-higgs|diphoton", t):
        add_tags(tags, "higgs")
    if re.search(
        r"dark photon|dark matter|dark sector|hidden sector|wimp|millicharged|dark srf",
        t,
    ):
        add_tags(tags, "dark-sector")

    if re.search(r"muon collider|mucol|\bimcc\b|muon smasher", t):
        add_tags(tags, "muon-collider")
    if re.search(
        r"\bcepc\b|\bfcc\b|\bilc\b|\bclic\b|cool copper|future circular|lepton collider|e\+e-|e\^\+e",
        t,
    ):
        add_tags(tags, "cepc-fcc")
    if re.search(r"\blhc\b|large hadron|\bcms\b|\batlas\b|run 2|13 tev", t):
        add_tags(tags, "lhc")
    if re.search(r"beam dump|beamdump|fixed.target|pip-ii|jefferson lab|\bdune\b|argoneut", t):
        add_tags(tags, "beamdump")

    if re.search(
        r"beyond standard model|\bbsm\b|new physics|exotic|resonance|extra dimension|"
        r"technicolor|composite|z'|z prime|w'|w prime|heavy scalar|top partner|colored",
        t,
    ):
        add_tags(tags, "bsm")

    if re.search(r"standard model|gg->|radiative decay z", t) and "beyond standard model" not in t:
        if not tags.intersection({"bsm", "supersymmetry", "axions", "dark-sector"}):
            add_tags(tags, "standard-model")

    if is_white and re.search(
        r"white paper|technical design|conceptual design|milestone|snowmass|community|working group",
        t,
    ):
        if not tags:
            add_tags(tags, "bsm")

    if not tags:
        add_tags(tags, "bsm")

    return tags


def _context_fillers(tags: set[str], text: str, section: str) -> list[str]:
    """Ordered optional tags inferred from context but not yet assigned."""
    t = text.lower()
    fillers: list[str] = []

    def offer(tag: str, cond: bool) -> None:
        if cond and tag not in tags and tag not in fillers:
            fillers.append(tag)

    offer("lhc", bool(re.search(r"\blhc\b|cms|atlas|run 2|13 tev|large hadron", t)))
    offer("muon-collider", bool(re.search(r"muon collider|mucol|\bimcc\b", t)))
    offer("cepc-fcc", bool(re.search(r"\bcepc\b|\bfcc\b|\bilc\b|lepton collider|snowmass", t)))
    offer("beamdump", bool(re.search(r"dune|argoneut|beam dump|pip-ii|jefferson lab", t)))
    offer("forward-physics", bool(re.search(r"forward|millicharged|mathusla", t)))
    offer("higgs", bool(re.search(r"\bhiggs\b|125 gev", t)))
    offer("eft", bool(re.search(r"wilson|effective field|\bsmeft\b", t)))
    offer("amplitudes", bool(re.search(r"amplitude|helicity|on-shell", t)))
    offer("bsm", section != "refereed_journals")

    if section != "refereed_journals" and "bsm" not in tags:
        if "bsm" not in fillers:
            fillers.append("bsm")

    return fillers


def enrich_tags(tags: set[str], text: str, section: str) -> set[str]:
    """Add companion and contextual tags; target 3–4 labels with minimum 2."""
    enriched = set(tags)

    for tag in list(enriched):
        for companion in COMPANION_TAGS.get(tag, []):
            enriched.add(companion)

    for filler in _context_fillers(enriched, text, section):
        if len(enriched) >= TARGET_TAGS:
            break
        enriched.add(filler)

    if len(enriched) < MIN_TAGS:
        if "bsm" not in enriched:
            enriched.add("bsm")
        elif len(enriched) < MIN_TAGS:
            for filler in _context_fillers(enriched, text, section):
                enriched.add(filler)
                if len(enriched) >= MIN_TAGS:
                    break
        if len(enriched) < MIN_TAGS and "lhc" not in enriched:
            enriched.add("lhc")

    # Prefer 3+ tags when context supports it, without exceeding target before ordering.
    if len(enriched) < 3:
        for filler in _context_fillers(enriched, text, section):
            enriched.add(filler)
            if len(enriched) >= 3:
                break

    return enriched


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
    limit = MAX_TAGS_OTHER if section != "refereed_journals" else MAX_TAGS_REFEREED
    ordered = [x for x in TAG_ORDER if x in tags][:limit]
    return ordered or ["bsm"]


def refined_tags_for_publication(
    pub: dict,
    root: Path,
    base_tags: set[str] | None = None,
    selected_seeds: dict[str, list[str]] | None = None,
    theme_seeds: dict[str, list[str]] | None = None,
) -> list[str]:
    arxiv = (pub.get("arxiv") or "").strip()
    pub_id = (pub.get("id") or "").strip()
    section = pub.get("section") or ""
    title = pub.get("title") or ""
    text = pub_text(pub)

    tags: set[str] = set(base_tags or [])

    if arxiv and arxiv in ARXIV_OVERRIDES:
        tags.update(ARXIV_OVERRIDES[arxiv])
    elif pub_id and pub_id in ID_OVERRIDES:
        tags.update(ID_OVERRIDES[pub_id])
    else:
        selected_seeds = selected_seeds if selected_seeds is not None else seed_from_selected(root)
        theme_seeds = theme_seeds if theme_seeds is not None else seed_from_themes(root)
        if arxiv:
            tags.update(selected_seeds.get(arxiv, []))
            tags.update(theme_seeds.get(arxiv, []))
        tags.update(infer_tags(title, section, text=text))

    tags = enrich_tags(tags, text, section)
    return order_tags(tags, section)


def draft_tags_for_publication(
    pub: dict,
    root: Path,
    selected_seeds: dict[str, list[str]] | None = None,
    theme_seeds: dict[str, list[str]] | None = None,
) -> list[str]:
    return refined_tags_for_publication(
        pub,
        root,
        base_tags=None,
        selected_seeds=selected_seeds,
        theme_seeds=theme_seeds,
    )
