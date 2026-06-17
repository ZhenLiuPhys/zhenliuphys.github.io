from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup


PUB_LIST_IDS = {"l1", "l2", "l3"}
TALK_LIST_IDS = {"l4", "l5", "l6"}
PUB_SECTION_MAP = {
    "l1": "refereed_journals",
    "l2": "other_publications_editor",
    "l3": "other_publications_contributor",
}

CV_INPUT_CANDIDATES = (
    Path("Material/ZhenLiu_CV.tex"),
)
DEFAULT_CV_INPUT = "Material/ZhenLiu_CV.tex"
DEFAULT_HAND_EDITS_PATH = "data/source/cv_hand_edits.yaml"
DEFAULT_CONFLICT_APPROVALS_TEMPLATE = "backups/cv-conflict-approvals.json"
ALLOWED_CV_SUFFIXES = {".tex", ".htm", ".html"}

SERVICE_SECTION_TITLES = {
    "workshops": "Program&Workshop organizations",
    "conference_sessions": "Conference&Workshop session organizations",
    "committee_membership": "Committee and Membership",
    "editorial_referee": "Journal Services",
    "referee_services": "Other Referee Services",
    "grant_review": "Grant (proposal) Review",
    "university_service": "Departmental Service",
}

REFEREE_SECTION_TITLE = (
    "Journal Referee Services "
    "(counting number of reports written; my average is around 1.5 reports per manuscript) "
    "(latest year of review service provided)"
)

REFEREE_JOURNAL_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9&'’.,/()\-\s]+?)\*\d+\s*\((?:19|20)\d{2}\)"
)
TEACHING_SECTION_TITLE = "Teaching Experience"
SUMMER_LECTURES_SECTION_TITLE = "Summer/Winter School Lectures"
TEACHING_TERM_FULL_RE = re.compile(r"^(Spring|Summer|Fall|Winter)\s+((?:19|20)\d{2})$", re.I)
TEACHING_YEAR_ONLY_RE = re.compile(r"^((?:19|20)\d{2})$")
COURSE_MATERIAL_URLS = {
    "Physics 8011": "https://github.com/ZhenLiuPhys/TeachingMaterial/tree/main/8011Fall2025",
}
MONTH_YEAR_HINT_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?(?:[-/]\w+)?\s*(?:19|20)\d{2}\b|\b(?:19|20)\d{2}\b",
    re.I,
)

PUB_CONFLICT_FIELDS = ("date", "journal_url", "doi", "arxiv")
TALK_CONFLICT_FIELDS = ("date", "event", "venue", "location", "slides_url", "video_url")

LECTURE_BLOB_RE = re.compile(
    r"\b("
    r"lecture(?:s)?"
    r"|lecture\s+series"
    r"|summer(?:\s|-)?s(?:chool|hool)"
    r"|summer(?:\s|-)?institute"
    r"|winter(?:\s|-)?s(?:chool|hool)"
    r"|spring(?:\s|-)?school"
    r"|autumn(?:\s|-)?school"
    r"|school\s+lecture(?:s)?"
    r"|mini(?:\s|-)?course"
    r")\b",
    re.I,
)
UMN_ADVISEE_LINE_RE = re.compile(r"\(umn,\s*(?:undergraduate|graduate)\)", re.I)
PHD_DETAIL_LINE_RE = re.compile(r"(?:Preliminary Exam|Thesis Defense).*Advisor:", re.I)
EXTERNAL_PHD_LINE_RE = re.compile(r"(?:Preliminary Exam|Thesis Defense)", re.I)


def resolve_cv_input(cli_path: str) -> Path:
    """Resolve CV input path and validate supported file extensions."""
    explicit = Path(cli_path)
    if cli_path != DEFAULT_CV_INPUT and not explicit.is_file():
        raise SystemExit(f"CV source not found: {explicit.as_posix()}")

    ordered: list[Path] = [explicit]
    for candidate in CV_INPUT_CANDIDATES:
        if candidate not in ordered:
            ordered.append(candidate)
    for candidate in ordered:
        if candidate.is_file():
            suffix = candidate.suffix.lower()
            if suffix not in ALLOWED_CV_SUFFIXES:
                allowed = ", ".join(sorted(ALLOWED_CV_SUFFIXES))
                raise SystemExit(
                    f"Unsupported CV input format: {candidate.as_posix()} (allowed: {allowed})"
                )
            return candidate
    names = " or ".join(str(p) for p in CV_INPUT_CANDIDATES)
    raise SystemExit(f"CV source not found. Expected one of: {names}")

MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_label_number(text: str) -> str:
    return re.sub(r"^\d+\.\s*", "", clean_text(text))


def extract_year(text: str) -> int | None:
    years = re.findall(r"\b((?:19|20)\d{2})\b", text)
    if not years:
        return None
    return int(years[-1])


def extract_arxiv(text: str, links: list[str]) -> str:
    for link in links:
        m = re.search(r"arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", link)
        if m:
            return m.group(1)
    m = re.search(r"\b([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)\b", text)
    return m.group(1) if m else ""


def extract_doi(text: str, links: list[str]) -> str:
    for link in links:
        m = re.search(r"(?:doi\.org|dx\.doi\.org)/(10\.\d{4,9}/[^\s?#]+)", link, re.I)
        if m:
            return m.group(1).rstrip(").,;")
        m2 = re.search(r"/(10\.\d{4,9}/[^/\s?#]+(?:/[^/\s?#]+)*)", link)
        if m2 and "arxiv.org" not in link:
            return m2.group(1).rstrip(").,;")
    m = re.search(r"(10\.\d{4,9}/[^\s,;()]+)", text)
    return m.group(1).rstrip(").,;") if m else ""


def infer_title(text: str) -> str:
    text = re.sub(r"^\d+\.\s*", "", text)
    text = text.strip()
    if not text:
        return "Untitled Entry"
    if "," in text:
        candidate = text.split(",", 1)[0].strip()
        if len(candidate) >= 8:
            text = candidate
    else:
        text = text[:180].strip()

    # Remove parser artifacts such as "(link)" from title display.
    text = re.sub(r"\(\s*link\s*\)", "", text, flags=re.I)
    text = re.sub(r"\[\s*link\s*\]", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" ,.-")
    return text or "Untitled Entry"


def infer_venue(text: str, title: str) -> str:
    tail = text.replace(title, "", 1).lstrip(", ").strip()
    tail = re.sub(r"\(\s*link\s*\),?\s*", "", tail, flags=re.I)
    tail = re.sub(r"\[\s*link\s*\],?\s*", "", tail, flags=re.I)
    if not tail:
        return ""
    if len(tail) > 220:
        tail = tail[:220].rstrip() + "..."
    return tail


def infer_talk_type(text: str) -> str:
    lower = text.lower()
    if "contributed" in lower:
        return "contributed"
    if "invited" in lower or "seminar" in lower or "colloquium" in lower:
        return "invited"
    return "talk"


def extract_month(text: str) -> int | None:
    lower = text.lower()
    for token, month in MONTH_MAP.items():
        if re.search(rf"\b{re.escape(token)}\.?\b", lower):
            return month
    return None


def infer_host(text: str) -> str:
    chunks = [c.strip() for c in text.split(",") if c.strip()]
    host_keywords = (
        "university",
        "institute",
        "laboratory",
        "lab",
        "fermilab",
        "cern",
        "ihep",
        "kitp",
        "aspen",
        "conference",
        "workshop",
        "school",
    )
    for chunk in reversed(chunks):
        lower = chunk.lower()
        if any(k in lower for k in host_keywords):
            return chunk
    return ""


def build_date(year: int | None, month: int | None = None) -> str:
    safe_year = year if year and year > 0 else 1900
    safe_month = month if month and 1 <= month <= 12 else 1
    return f"{safe_year:04d}-{safe_month:02d}-01"


def publication_date(year: int, arxiv: str, raw_text: str) -> str:
    if arxiv and re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", arxiv):
        yy = int(arxiv[:2])
        mm = int(arxiv[2:4])
        full_year = 2000 + yy
        if 1 <= mm <= 12:
            return build_date(full_year, mm)
    return build_date(year, extract_month(raw_text))


def talk_date(year: int, raw_text: str) -> str:
    return build_date(year, extract_month(raw_text))


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:96] or "item"


def load_yaml_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def load_yaml_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _normalize_value(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value


def _values_conflict(old_value, new_value) -> bool:
    if not (_has_value(old_value) and _has_value(new_value)):
        return False
    return _normalize_value(old_value) != _normalize_value(new_value)


def _display_value(value, limit: int = 180) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def detect_list_field_conflicts(
    *,
    output_name: str,
    item_kind: str,
    old_items: list[dict],
    new_items: list[dict],
    fields: tuple[str, ...],
) -> list[dict]:
    conflicts: list[dict] = []
    old_by_id = {str(item.get("id") or ""): item for item in old_items if item.get("id")}
    new_by_id = {str(item.get("id") or ""): item for item in new_items if item.get("id")}
    common_ids = sorted(set(old_by_id) & set(new_by_id))
    for item_id in common_ids:
        old_item = old_by_id[item_id]
        new_item = new_by_id[item_id]
        for field in fields:
            old_value = old_item.get(field)
            new_value = new_item.get(field)
            if not _values_conflict(old_value, new_value):
                continue
            conflicts.append(
                {
                    "output": output_name,
                    "kind": item_kind,
                    "id": item_id,
                    "field": field,
                    "old": old_value,
                    "new": new_value,
                }
            )
    return conflicts


def _iter_service_teaching_conflicts(
    *,
    output_name: str,
    old_data: dict,
    new_data: dict,
) -> list[dict]:
    conflicts: list[dict] = []
    for section in sorted(set(old_data) & set(new_data)):
        old_section = old_data.get(section)
        new_section = new_data.get(section)
        if isinstance(old_section, list) and isinstance(new_section, list):
            limit = min(len(old_section), len(new_section))
            for idx in range(limit):
                old_item = old_section[idx]
                new_item = new_section[idx]
                if isinstance(old_item, dict) and isinstance(new_item, dict):
                    for field in sorted(set(old_item) | set(new_item)):
                        old_value = old_item.get(field)
                        new_value = new_item.get(field)
                        if not _values_conflict(old_value, new_value):
                            continue
                        conflicts.append(
                            {
                                "output": output_name,
                                "kind": "section_item_field",
                                "section": section,
                                "index": idx,
                                "field": field,
                                "old": old_value,
                                "new": new_value,
                            }
                        )
                elif _values_conflict(old_item, new_item):
                    conflicts.append(
                        {
                            "output": output_name,
                            "kind": "section_item",
                            "section": section,
                            "index": idx,
                            "old": old_item,
                            "new": new_item,
                        }
                    )
            continue
        if _values_conflict(old_section, new_section):
            conflicts.append(
                {
                    "output": output_name,
                    "kind": "section",
                    "section": section,
                    "old": old_section,
                    "new": new_section,
                }
            )
    return conflicts


def _iter_mentoring_conflicts(
    *,
    output_name: str,
    old_data: dict,
    new_data: dict,
) -> list[dict]:
    conflicts: list[dict] = []
    sections = sorted(set(old_data) | set(new_data))
    for section in sections:
        old_list = old_data.get(section) or []
        new_list = new_data.get(section) or []
        if not isinstance(old_list, list) or not isinstance(new_list, list):
            continue
        old_by_name = {
            str(item.get("name") or "").lower(): item
            for item in old_list
            if isinstance(item, dict) and item.get("name")
        }
        for new_item in new_list:
            if not isinstance(new_item, dict):
                continue
            name = str(new_item.get("name") or "").lower()
            old_item = old_by_name.get(name)
            if not old_item:
                continue
            for field in sorted(set(old_item) | set(new_item)):
                if field == "profile_url":
                    continue
                old_value = old_item.get(field)
                new_value = new_item.get(field)
                if not _values_conflict(old_value, new_value):
                    continue
                conflicts.append(
                    {
                        "output": output_name,
                        "kind": "section_item_field",
                        "section": section,
                        "id": new_item.get("name"),
                        "field": field,
                        "old": old_value,
                        "new": new_value,
                    }
                )
    return conflicts


def detect_import_conflicts(
    *,
    old_publications: list[dict],
    new_publications: list[dict],
    old_talks: list[dict],
    new_talks: list[dict],
    old_service: dict,
    new_service: dict,
    old_teaching: dict,
    new_teaching: dict,
    old_mentoring: dict | None = None,
    new_mentoring: dict | None = None,
) -> dict:
    conflicts = {
        "publications": detect_list_field_conflicts(
            output_name="publications",
            item_kind="publication",
            old_items=old_publications,
            new_items=new_publications,
            fields=PUB_CONFLICT_FIELDS,
        ),
        "talks": detect_list_field_conflicts(
            output_name="talks",
            item_kind="talk",
            old_items=old_talks,
            new_items=new_talks,
            fields=TALK_CONFLICT_FIELDS,
        ),
        "service": _iter_service_teaching_conflicts(
            output_name="service",
            old_data=old_service,
            new_data=new_service,
        ),
        "teaching": _iter_service_teaching_conflicts(
            output_name="teaching",
            old_data=old_teaching,
            new_data=new_teaching,
        ),
        "mentoring": _iter_mentoring_conflicts(
            output_name="mentoring",
            old_data=old_mentoring or {},
            new_data=new_mentoring or {},
        ),
    }
    conflicts["counts"] = {k: len(v) for k, v in conflicts.items() if k != "counts"}
    conflicts["total"] = sum(conflicts["counts"].values())
    return conflicts


def finalize_cv_import(
    *,
    old_publications: list[dict],
    new_publications: list[dict],
    old_talks: list[dict],
    new_talks: list[dict],
    old_service: dict,
    new_service: dict,
    old_teaching: dict,
    new_teaching: dict,
    old_mentoring: dict,
    new_mentoring: dict,
    hand_edits_path: Path,
    conflict_approvals_path: Path | None,
    approve_conflicts: bool,
    conflict_report_path: Path | None,
    approvals_template_path: Path | None,
    rerun_hint: str,
) -> dict:
    from cv_hand_edits import (
        RESOLUTION_ACCEPT_CV,
        conflict_key,
        load_conflict_approvals,
        load_hand_edits,
        resolve_import_data,
        save_hand_edits,
    )

    registry = load_hand_edits(hand_edits_path)
    approvals = load_conflict_approvals(conflict_approvals_path)

    resolved = resolve_import_data(
        old_publications=old_publications,
        new_publications=new_publications,
        old_talks=old_talks,
        new_talks=new_talks,
        old_service=old_service,
        new_service=new_service,
        old_teaching=old_teaching,
        new_teaching=new_teaching,
        old_mentoring=old_mentoring,
        new_mentoring=new_mentoring,
        pub_fields=PUB_CONFLICT_FIELDS,
        talk_fields=TALK_CONFLICT_FIELDS,
        registry=registry,
        approvals=approvals,
    )

    pending = list(resolved["pending_conflicts"])
    if approve_conflicts and pending:
        for conflict in pending:
            approvals[conflict_key(conflict)] = RESOLUTION_ACCEPT_CV
        resolved = resolve_import_data(
            old_publications=old_publications,
            new_publications=new_publications,
            old_talks=old_talks,
            new_talks=new_talks,
            old_service=old_service,
            new_service=new_service,
            old_teaching=old_teaching,
            new_teaching=new_teaching,
            old_mentoring=old_mentoring,
            new_mentoring=new_mentoring,
            pub_fields=PUB_CONFLICT_FIELDS,
            talk_fields=TALK_CONFLICT_FIELDS,
            registry=resolved["registry"],
            approvals=approvals,
        )
        pending = list(resolved["pending_conflicts"])

    enforce_conflict_gate(
        preserved_conflicts=resolved["preserved_conflicts"],
        pending_conflicts=pending,
        approve_conflicts=False,
        report_path=conflict_report_path,
        approvals_template_path=approvals_template_path,
        rerun_hint=rerun_hint,
    )

    save_hand_edits(hand_edits_path, resolved["registry"])
    return resolved


def _format_conflict_line(conflict: dict) -> str:
    if conflict.get("id"):
        target = f"{conflict.get('kind')} {conflict.get('id')}"
    elif conflict.get("section") is not None and conflict.get("index") is not None:
        target = f"{conflict.get('section')}[{conflict.get('index')}]"
    elif conflict.get("section") is not None:
        target = str(conflict.get("section"))
    else:
        target = "entry"
    field = conflict.get("field")
    field_part = f".{field}" if field else ""
    old_str = _display_value(conflict.get("old"))
    new_str = _display_value(conflict.get("new"))
    return f"- {target}{field_part}: old={old_str} | new={new_str}"


def maybe_write_conflict_report(conflicts: dict, report_path: Path | None) -> None:
    if not report_path:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(conflicts, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote conflict report to {report_path}")


def enforce_conflict_gate(
    *,
    preserved_conflicts: list[dict],
    pending_conflicts: list[dict],
    approve_conflicts: bool,
    report_path: Path | None,
    approvals_template_path: Path | None,
    rerun_hint: str,
) -> None:
    from cv_hand_edits import format_conflict_for_review, write_conflict_approvals_template

    report = {
        "preserved": preserved_conflicts,
        "pending": pending_conflicts,
        "counts": {
            "preserved": len(preserved_conflicts),
            "pending": len(pending_conflicts),
            "total": len(preserved_conflicts) + len(pending_conflicts),
        },
    }
    maybe_write_conflict_report(report, report_path)

    if preserved_conflicts:
        print(f"Preserved {len(preserved_conflicts)} hand-edited conflict(s); manual values kept.")

    pending = list(pending_conflicts)
    if approve_conflicts and pending:
        print("Warning: --approve-conflicts accepts all pending CV values and marks them hand-edited.")
        pending = []

    if not pending:
        return

    print(f"Pending approval for {len(pending)} conflict(s):")
    preview_limit = 30
    for conflict in pending[:preview_limit]:
        print(format_conflict_for_review(conflict))
    if len(pending) > preview_limit:
        print(f"... and {len(pending) - preview_limit} more pending conflicts.")

    if approvals_template_path:
        write_conflict_approvals_template(approvals_template_path, pending)
        print(f"Wrote approval template to {approvals_template_path}")

    print("Conflicts detected. No files were written.")
    print("Hand-edited fields are always kept. For the rest, reply with keep_manual or accept_cv per conflict.")
    print(f"Re-run with approvals: {rerun_hint}")
    raise SystemExit(2)


def _section_lines_between(start_node, end_node, strip_labels: bool = True) -> list[str]:
    lines: list[str] = []
    node = start_node.next_sibling
    while node and node is not end_node:
        if getattr(node, "name", None) == "p":
            t = clean_text(node.get_text(" ", strip=True))
            if strip_labels:
                t = strip_label_number(t)
            if t:
                lines.append(t)
        node = node.next_sibling
    return lines


def _textbox_title_map(soup: BeautifulSoup) -> tuple[list, dict[str, int]]:
    textboxes = []
    index_by_title: dict[str, int] = {}
    for box in soup.find_all("div", class_="textbox"):
        title = clean_text(box.get_text(" ", strip=True))
        if not title:
            continue
        idx = len(textboxes)
        textboxes.append(box)
        index_by_title[title] = idx
    return textboxes, index_by_title


def _unique_keep_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _has_date_hint(text: str) -> bool:
    return bool(MONTH_YEAR_HINT_RE.search(text or ""))


def normalize_service_entries(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    for chunk in [clean_text(line) for line in lines if clean_text(line)]:
        if not normalized:
            normalized.append(chunk)
            continue

        prev = normalized[-1]
        lower = chunk.lower()
        continuation = (
            lower.startswith(("on the ", "by ", "the ", "and "))
            or (_has_date_hint(chunk) and not _has_date_hint(prev))
            or len(chunk.split()) <= 2
        )
        if continuation:
            normalized[-1] = clean_text(f"{prev} {chunk}")
        else:
            normalized.append(chunk)
    return _unique_keep_order([item for item in normalized if item])


def _external_phd_entry(line: str) -> str:
    parts = [clean_text(p) for p in line.split(",") if clean_text(p)]
    if len(parts) < 2:
        return ""
    name = parts[0]
    institution = parts[-1]
    if not name or not institution or name.lower() == institution.lower():
        return ""
    return f"{name}, {institution}"


def normalize_university_service_entries(lines: list[str]) -> list[str]:
    cleaned = [clean_text(line) for line in lines if clean_text(line)]
    out: list[str] = []
    phd_names: list[str] = []
    external_entries: list[str] = []
    in_external = False
    collecting_phd = False

    def flush_phd() -> None:
        nonlocal collecting_phd
        if phd_names:
            count = len(phd_names)
            label = "student" if count == 1 else "students"
            out.append(f"PhD committee (UMN): {count} {label}")
            phd_names.clear()
        collecting_phd = False

    def flush_external() -> None:
        nonlocal in_external
        if external_entries:
            count = len(external_entries)
            label = "external student" if count == 1 else "external students"
            out.append(f"PhD committee (External): {count} {label}")
            external_entries.clear()
        in_external = False

    for line in cleaned:
        lower = line.lower()
        if "graduate and undergraduate academic advisees" in lower:
            continue
        if "providing academic progress advising" in lower:
            continue
        if UMN_ADVISEE_LINE_RE.search(line):
            continue
        if lower.startswith("advisor:"):
            continue

        if lower.startswith("(external)"):
            flush_phd()
            in_external = True
            continue

        is_phd_start = lower.startswith("phd committee:")
        is_phd_detail = bool(PHD_DETAIL_LINE_RE.search(line))
        if in_external and (is_phd_detail or EXTERNAL_PHD_LINE_RE.search(line)):
            entry = _external_phd_entry(line)
            if entry and entry not in external_entries:
                external_entries.append(entry)
            continue

        if not in_external and (is_phd_start or (collecting_phd and is_phd_detail) or (phd_names and is_phd_detail)):
            collecting_phd = True
            name_source = line
            if ":" in name_source and lower.startswith("phd committee"):
                name_source = name_source.split(":", 1)[1]
            name = clean_text(name_source.split(",", 1)[0]).strip("'\"")
            if name and name not in phd_names:
                phd_names.append(name)
            continue

        if collecting_phd:
            flush_phd()
        if in_external:
            flush_external()
        out.append(line)

    flush_phd()
    flush_external()
    return _unique_keep_order(out)


def extract_refereed_journals(referee_lines: list[str]) -> list[str]:
    blob = " ".join(referee_lines)
    journals = [clean_text(name).rstrip(" ,.;") for name in REFEREE_JOURNAL_RE.findall(blob)]
    return _unique_keep_order([j for j in journals if j])


def parse_service_data(soup: BeautifulSoup) -> dict:
    textboxes, by_title = _textbox_title_map(soup)
    service: dict[str, list[str]] = {}
    for key, title in SERVICE_SECTION_TITLES.items():
        idx = by_title.get(title)
        if idx is None:
            service[key] = []
            continue
        start = textboxes[idx]
        end = textboxes[idx + 1] if idx + 1 < len(textboxes) else None
        lines = _section_lines_between(start, end)
        service[key] = normalize_service_entries(lines)

    referee_idx = by_title.get(REFEREE_SECTION_TITLE)
    referee_lines: list[str] = []
    if referee_idx is not None:
        start = textboxes[referee_idx]
        end = textboxes[referee_idx + 1] if referee_idx + 1 < len(textboxes) else None
        referee_lines = _section_lines_between(start, end)
    service["referee_journals"] = extract_refereed_journals(referee_lines)

    service["editorial_referee"] = normalize_service_entries(service.get("editorial_referee", []))
    service["referee_services"] = normalize_service_entries(service.get("referee_services", []))
    service["grant_review"] = normalize_service_entries(service.get("grant_review", []))
    service["university_service"] = normalize_service_entries(service.get("university_service", []))
    service["university_service"] = normalize_university_service_entries(service.get("university_service", []))
    service["workshops"] = normalize_service_entries(service.get("workshops", []))
    service["conference_sessions"] = normalize_service_entries(service.get("conference_sessions", []))
    service["committee_membership"] = normalize_service_entries(service.get("committee_membership", []))
    return service


def parse_teaching_data(soup: BeautifulSoup) -> dict:
    textboxes, by_title = _textbox_title_map(soup)
    idx = by_title.get(TEACHING_SECTION_TITLE)
    if idx is None:
        return {"courses_umn": []}
    start = textboxes[idx]
    end = textboxes[idx + 1] if idx + 1 < len(textboxes) else None
    lines = _section_lines_between(start, end)

    courses: list[dict] = []
    for line in lines:
        parts = re.split(r"(?=Physics\s+\d{4}[A-Z]?\s*,)", line)
        for part in parts:
            parsed = parse_teaching_course_entry(part)
            if parsed:
                courses.append(parsed)
    return {"courses_umn": merge_teaching_courses(courses)}


def parse_teaching_course_entry(raw: str) -> dict | None:
    text = clean_text(raw).strip(" ,;")
    if not text:
        return None

    m = re.match(r"^(Physics\s+\d{4}[A-Z]?)\s*,\s*(.+)$", text)
    if not m:
        return {"title": text, "terms": []}

    code = clean_text(m.group(1))
    remainder = clean_text(m.group(2))
    tokens = [clean_text(tok) for tok in remainder.split(",") if clean_text(tok)]
    if not tokens:
        return {"code": code, "title": "", "terms": []}

    first_term_idx = -1
    for i, tok in enumerate(tokens):
        if TEACHING_TERM_FULL_RE.match(tok) or TEACHING_YEAR_ONLY_RE.match(tok):
            first_term_idx = i
            break

    if first_term_idx < 0:
        title = ", ".join(tokens).strip()
        term_tokens: list[str] = []
    else:
        title = ", ".join(tokens[:first_term_idx]).strip(" ,")
        term_tokens = tokens[first_term_idx:]

    terms: list[str] = []
    current_season = ""
    for tok in term_tokens:
        full = TEACHING_TERM_FULL_RE.match(tok)
        if full:
            season = full.group(1).title()
            year = full.group(2)
            current_season = season
            terms.append(f"{season} {year}")
            continue
        year_only = TEACHING_YEAR_ONLY_RE.match(tok)
        if year_only:
            year = year_only.group(1)
            if current_season:
                terms.append(f"{current_season} {year}")
            else:
                terms.append(year)

    out = {
        "code": code,
        "title": title,
        "terms": _unique_keep_order([t for t in terms if t]),
    }
    material_url = COURSE_MATERIAL_URLS.get(code)
    if material_url:
        out["course_material_url"] = material_url
    return out


def merge_teaching_courses(courses: list[dict]) -> list[dict]:
    merged: list[dict] = []
    by_key: dict[tuple[str, str], int] = {}
    for row in courses:
        code = clean_text(str(row.get("code") or ""))
        title = clean_text(str(row.get("title") or ""))
        terms = [clean_text(str(t)) for t in (row.get("terms") or []) if clean_text(str(t))]
        key = (code.lower(), title.lower())
        if key in by_key:
            idx = by_key[key]
            existing = merged[idx]
            existing_terms = existing.get("terms") or []
            existing["terms"] = _unique_keep_order(existing_terms + terms)
            if not existing.get("course_material_url") and row.get("course_material_url"):
                existing["course_material_url"] = row.get("course_material_url")
            continue
        out = {}
        if code:
            out["code"] = code
        if title:
            out["title"] = title
        out["terms"] = _unique_keep_order(terms)
        if row.get("course_material_url"):
            out["course_material_url"] = row.get("course_material_url")
        merged.append(out)
        by_key[key] = len(merged) - 1
    return merged


def parse_summer_winter_lecture_talks(soup: BeautifulSoup, source: str) -> list[dict]:
    textboxes, by_title = _textbox_title_map(soup)
    idx = by_title.get(SUMMER_LECTURES_SECTION_TITLE)
    if idx is None:
        return []
    start = textboxes[idx]
    end = textboxes[idx + 1] if idx + 1 < len(textboxes) else None
    lines = _section_lines_between(start, end, strip_labels=False)

    entries: list[tuple[str, str]] = []
    current_title = ""
    current_event_parts: list[str] = []
    for line in lines:
        m = re.match(r"^\d+\.\s*(.+)$", line)
        if m:
            if current_title:
                entries.append((current_title, clean_text(" ".join(current_event_parts))))
            current_title = clean_text(m.group(1))
            current_event_parts = []
        elif current_title:
            current_event_parts.append(line)

    if current_title:
        entries.append((current_title, clean_text(" ".join(current_event_parts))))

    # Handle merged title+event rows where Word export put both on one numbered line.
    fixed_entries: list[tuple[str, str]] = []
    for title, event in entries:
        if event:
            fixed_entries.append((title, event))
            continue
        split_markers = (
            "Fudan Particle Physics Summer School",
            "Summer Institute",
            "Summer School",
            "Winter School",
            "TASI ",
            "KEK-PH",
        )
        split_at = -1
        for marker in split_markers:
            idx = title.find(marker)
            if idx > 0 and (split_at < 0 or idx < split_at):
                split_at = idx
        if split_at > 0:
            fixed_entries.append(
                (
                    clean_text(title[:split_at]),
                    clean_text(title[split_at:]),
                )
            )
        else:
            fixed_entries.append((title, ""))

    talks: list[dict] = []
    for idx, (title, event) in enumerate(fixed_entries, start=1):
        raw = f"{title}, {event}" if event else title
        year = extract_year(raw) or 1900
        talks.append(
            {
                "id": f"talk-lecture-sw-{idx:03d}-{slugify(title)}",
                "title": title,
                "year": year,
                "date": talk_date(year, raw),
                "event": event,
                "host": infer_host(event),
                "location": "",
                "talk_type": infer_talk_type(raw),
                "slides_url": "",
                "video_url": "",
                "source": source,
                "raw_text": raw,
            }
        )
    return talks


def merge_talk_lists(base_talks: list[dict], extra_talks: list[dict]) -> list[dict]:
    if not extra_talks:
        return base_talks
    merged = list(base_talks)
    seen = {
        (
            clean_text(str(t.get("title") or "")).lower(),
            str(t.get("date") or ""),
        )
        for t in base_talks
    }
    for talk in extra_talks:
        key = (
            clean_text(str(talk.get("title") or "")).lower(),
            str(talk.get("date") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(talk)
    merged.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("year") or 0), str(x.get("title") or "")), reverse=True)
    return merged


def is_lecture_talk(talk: dict) -> bool:
    category = (talk.get("category") or "").lower()
    if category == "lecture":
        return True
    blob = " ".join(
        str(talk.get(k) or "")
        for k in ("title", "event", "venue", "raw_text", "event_display")
    ).lower()
    return bool(LECTURE_BLOB_RE.search(blob))


def preserve_missing_lecture_talks(new_talks: list[dict], old_talks: list[dict]) -> tuple[list[dict], int]:
    new_ids = {str(t.get("id") or "") for t in new_talks}
    preserved: list[dict] = []
    for old in old_talks:
        old_id = str(old.get("id") or "")
        if old_id and old_id in new_ids:
            continue
        # Summer/Winter lecture items are auto-generated from CV each run.
        # Do not preserve stale legacy rows with outdated parser IDs.
        if old_id.startswith("talk-lecture-sw-"):
            continue
        if is_lecture_talk(old):
            preserved.append(old)
    if not preserved:
        return new_talks, 0
    merged = list(new_talks) + preserved
    merged.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("year") or 0), str(x.get("title") or "")), reverse=True)
    return merged, len(preserved)


def summarize_changes(kind: str, old_items: list[dict], new_items: list[dict]) -> None:
    old_by_id = {str(item.get("id") or ""): item for item in old_items if item.get("id")}
    new_by_id = {str(item.get("id") or ""): item for item in new_items if item.get("id")}
    added = sorted(set(new_by_id) - set(old_by_id))
    removed = sorted(set(old_by_id) - set(new_by_id))
    changed: list[str] = []
    fields = ("title", "date", "venue", "location", "talk_type", "category")
    for item_id in sorted(set(old_by_id) & set(new_by_id)):
        old = old_by_id[item_id]
        new = new_by_id[item_id]
        if any((old.get(f) or "") != (new.get(f) or "") for f in fields):
            changed.append(item_id)
    print(
        f"{kind} summary: +{len(added)} added, -{len(removed)} removed, ~{len(changed)} updated"
    )
    if added:
        print(f"  added (sample): {', '.join(added[:5])}")
    if removed:
        print(f"  removed (sample): {', '.join(removed[:5])}")
    if changed:
        print(f"  updated (sample): {', '.join(changed[:5])}")


def featured_arxiv_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    for path in (
        root / "data" / "source" / "selected_publications.yaml",
        root / "data" / "selected_publications.yaml",
    ):
        for row in load_yaml_list(path):
            arxiv = (row.get("arxiv") or "").strip()
            if arxiv:
                ids.add(arxiv)
    return ids


def apply_featured_flags(publications: list[dict], root: Path, pub_out: Path) -> None:
    selected = featured_arxiv_ids(root)
    for item in publications:
        arxiv = (item.get("arxiv") or "").strip()
        item["featured"] = bool(arxiv and arxiv in selected)


def parse_entries(soup: BeautifulSoup, source: str) -> tuple[list[dict], list[dict]]:
    publications: list[dict] = []
    talks: list[dict] = []

    for ol in soup.find_all("ol"):
        list_id = ol.get("id", "")
        if list_id not in PUB_LIST_IDS and list_id not in TALK_LIST_IDS:
            continue

        for idx, li in enumerate(ol.find_all("li"), start=1):
            raw = clean_text(li.get_text(" ", strip=True))
            if not raw:
                continue

            links = []
            for a in li.find_all("a"):
                href = (a.get("href") or "").strip()
                if href.startswith("http"):
                    links.append(href)
            links = list(dict.fromkeys(links))

            title = infer_title(raw)
            year = extract_year(raw) or 1900
            arxiv = extract_arxiv(raw, links)
            doi = extract_doi(raw, links)
            journal_url = ""
            for link in links:
                if "arxiv.org" in link:
                    continue
                if "doi.org" in link or "dx.doi.org" in link:
                    continue
                journal_url = link
                break

            if list_id in PUB_LIST_IDS:
                item = {
                    "id": f"pub-{list_id}-{idx:03d}-{slugify(title)}",
                    "title": title,
                    "year": year,
                    "date": publication_date(year, arxiv, raw),
                    "authors": "",
                    "venue": infer_venue(raw, title),
                    "doi": doi,
                    "arxiv": arxiv,
                    "journal_url": journal_url,
                    "section": PUB_SECTION_MAP.get(list_id, "other"),
                    "featured": False,
                    "source": source,
                    "raw_text": raw,
                }
                publications.append(item)
            else:
                item = {
                    "id": f"talk-{list_id}-{idx:03d}-{slugify(title)}",
                    "title": title,
                    "year": year,
                    "date": talk_date(year, raw),
                    "event": infer_venue(raw, title),
                    "host": infer_host(infer_venue(raw, title)),
                    "location": "",
                    "talk_type": infer_talk_type(raw),
                    "slides_url": next((u for u in links if "indico" in u or "slides" in u or "pdf" in u), ""),
                    "video_url": next((u for u in links if "youtube.com" in u or "youtu.be" in u or "video" in u), ""),
                    "source": source,
                    "raw_text": raw,
                }
                talks.append(item)

    publications.sort(key=lambda x: (x["year"], x["title"]), reverse=True)
    talks.sort(key=lambda x: (x["year"], x["title"]), reverse=True)

    from clean_bibliography_data import normalize_publication, normalize_talk

    publications = [normalize_publication(p) for p in publications]
    talks = [normalize_talk(t) for t in talks]
    return publications, talks


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse CV source (TeX-first) into Hugo YAML data files.")
    parser.add_argument(
        "--input",
        default=DEFAULT_CV_INPUT,
        help="CV source path (default: Material/ZhenLiu_CV.tex)",
    )
    parser.add_argument("--pub-output", default="data/publications.yaml")
    parser.add_argument("--talk-output", default="data/talks.yaml")
    parser.add_argument("--service-output", default="data/source/service.yaml")
    parser.add_argument("--teaching-output", default="data/source/teaching.yaml")
    parser.add_argument("--mentoring-output", default="data/source/mentoring.yaml")
    parser.add_argument("--hand-edits", default=DEFAULT_HAND_EDITS_PATH)
    parser.add_argument(
        "--conflict-approvals",
        default="",
        help="JSON file listing per-conflict resolutions (keep_manual or accept_cv).",
    )
    parser.add_argument(
        "--write-approvals-template",
        default=DEFAULT_CONFLICT_APPROVALS_TEMPLATE,
        help="When conflicts need approval, write a fill-in JSON template to this path.",
    )
    parser.add_argument(
        "--approve-conflicts",
        action="store_true",
        help="Accept all pending CV values and mark them hand-edited (use only after review).",
    )
    parser.add_argument(
        "--conflict-report",
        default="",
        help="Optional JSON path to write detailed conflict report.",
    )
    args = parser.parse_args()

    hand_edits_path = Path(args.hand_edits)
    conflict_approvals_path = Path(args.conflict_approvals) if args.conflict_approvals else None
    approvals_template_path = Path(args.write_approvals_template) if args.write_approvals_template else None
    conflict_report_path = Path(args.conflict_report) if args.conflict_report else None

    input_path = resolve_cv_input(args.input)
    source_label = input_path.as_posix()
    rerun_suffix = f" --input {source_label}" if args.input else ""

    if input_path.suffix.lower() == ".tex":
        print(f"Detected TeX CV input: {source_label}")
        print("Running TeX parsing pipeline.")
        from parse_cv_tex import run_tex_pipeline

        run_tex_pipeline(
            input_path=input_path,
            pub_out=Path(args.pub_output),
            talk_out=Path(args.talk_output),
            service_out=Path(args.service_output),
            teaching_out=Path(args.teaching_output),
            mentoring_out=Path(args.mentoring_output),
            hand_edits_path=hand_edits_path,
            approve_conflicts=bool(args.approve_conflicts),
            conflict_report_path=conflict_report_path,
            conflict_approvals_path=conflict_approvals_path,
            approvals_template_path=approvals_template_path,
        )
        return

    html_text = input_path.read_text(encoding="utf-8", errors="ignore")
    print(f"Detected HTML CV input: {source_label}")
    print("Running legacy HTML parsing pipeline.")
    soup = BeautifulSoup(html_text, "html.parser")
    publications, talks = parse_entries(soup, source_label)
    lecture_talks = parse_summer_winter_lecture_talks(soup, source_label)
    service = parse_service_data(soup)
    teaching = parse_teaching_data(soup)

    pub_out = Path(args.pub_output)
    talk_out = Path(args.talk_output)
    service_out = Path(args.service_output)
    teaching_out = Path(args.teaching_output)
    mentoring_out = Path(args.mentoring_output)
    pub_out.parent.mkdir(parents=True, exist_ok=True)
    talk_out.parent.mkdir(parents=True, exist_ok=True)
    service_out.parent.mkdir(parents=True, exist_ok=True)
    teaching_out.parent.mkdir(parents=True, exist_ok=True)
    mentoring_out.parent.mkdir(parents=True, exist_ok=True)
    old_pubs = load_yaml_list(pub_out)
    old_talks = load_yaml_list(talk_out)
    old_service = load_yaml_dict(service_out)
    old_teaching = load_yaml_dict(teaching_out)
    old_mentoring = load_yaml_dict(mentoring_out)

    root = Path(__file__).resolve().parent.parent
    apply_featured_flags(publications, root, pub_out)
    from clean_bibliography_data import normalize_talk

    lecture_talks = [normalize_talk(t) for t in lecture_talks]
    talks = merge_talk_lists(talks, lecture_talks)
    talks, preserved_count = preserve_missing_lecture_talks(talks, old_talks)

    rerun_hint = (
        f"{sys.executable} scripts/parse_cv_html.py --conflict-approvals backups/cv-conflict-approvals.json"
        + rerun_suffix
    )
    resolved = finalize_cv_import(
        old_publications=old_pubs,
        new_publications=publications,
        old_talks=old_talks,
        new_talks=talks,
        old_service=old_service,
        new_service=service,
        old_teaching=old_teaching,
        new_teaching=teaching,
        old_mentoring=old_mentoring,
        new_mentoring={},
        hand_edits_path=hand_edits_path,
        conflict_approvals_path=conflict_approvals_path,
        approve_conflicts=bool(args.approve_conflicts),
        conflict_report_path=conflict_report_path,
        approvals_template_path=approvals_template_path,
        rerun_hint=rerun_hint,
    )
    publications = resolved["publications"]
    talks = resolved["talks"]
    service = resolved["service"]
    teaching = resolved["teaching"]

    from sync_publication_tags import apply_publication_tags

    tag_warnings = apply_publication_tags(publications, root)
    for msg in tag_warnings:
        print(f"Warning: {msg}", file=sys.stderr)

    pub_out.write_text(yaml.safe_dump(publications, sort_keys=False, allow_unicode=True), encoding="utf-8")
    talk_out.write_text(yaml.safe_dump(talks, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if any(service.get(k) for k in service):
        service_out.write_text(
            yaml.safe_dump(service, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    if any(teaching.get(k) for k in teaching):
        teaching_out.write_text(
            yaml.safe_dump(teaching, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    print(f"Parsed CV HTML: {source_label}")
    print(f"Wrote {len(publications)} publication entries to {pub_out}")
    print(f"Wrote {len(talks)} talk entries to {talk_out}")
    if lecture_talks:
        print(f"Extracted {len(lecture_talks)} summer/winter school lecture entries.")
    if any(service.get(k) for k in service):
        print(f"Wrote service entries to {service_out}")
        print(f"Extracted {len(service.get('referee_journals', []))} refereed journals.")
    else:
        print("Warning: no service sections detected; leaving service YAML unchanged.")
    if any(teaching.get(k) for k in teaching):
        print(f"Wrote teaching entries to {teaching_out}")
    else:
        print("Warning: no teaching section detected; leaving teaching YAML unchanged.")
    if preserved_count:
        print(f"Preserved {preserved_count} lecture entries missing from current CV import.")
    summarize_changes("Publication import", old_pubs, publications)
    summarize_changes("Talk import", old_talks, talks)


if __name__ == "__main__":
    main()
