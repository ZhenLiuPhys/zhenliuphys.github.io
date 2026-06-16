from __future__ import annotations

import re
from pathlib import Path

import yaml

from parse_cv_html import (
    PUB_SECTION_MAP,
    REFEREE_JOURNAL_RE,
    apply_featured_flags,
    extract_arxiv,
    extract_doi,
    extract_year,
    finalize_cv_import,
    infer_host,
    infer_talk_type,
    infer_title,
    infer_venue,
    is_lecture_talk,
    load_yaml_dict,
    load_yaml_list,
    merge_teaching_courses,
    normalize_university_service_entries,
    parse_teaching_course_entry,
    publication_date,
    slugify,
    summarize_changes,
    talk_date,
)

ROLE_PREFIXES = (
    "Organizer",
    "Organizing Committee",
    "Convener",
    "Chair",
    "Panelist",
    "Academic Committee",
    "Scientific Program Committee",
    "Scientific Program",
    "Committee",
    "Local coordinator",
    "Collaboration Member",
    "Member",
    "Fellow",
    "Editorial Board Member",
    "Internal Review",
    "Book Review",
)

DATE_TAIL_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Spring|Summer|Fall|Winter)"
    r"[^,;]*\d{4}(?:\s*---\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Spring|Summer|Fall|Winter)"
    r"[^,;]*\d{4})?)$",
    re.I,
)

URL_PERCENT_ESCAPE_RE = re.compile(r"^[0-9A-Fa-f]{2}$")
LATEX_TEXT_REPLACEMENTS = (
    (r"\rightarrow", "->"),
    (r"\to", "->"),
    (r"\gamma", "gamma"),
    (r"\Gamma", "Gamma"),
    (r"\tau", "tau"),
    (r"\mu", "mu"),
    (r"\nu", "nu"),
    (r"\ell", "l"),
)


def strip_tex_comments(text: str) -> str:
    out_lines: list[str] = []
    for line in text.splitlines():
        i = 0
        escaped = False
        buf: list[str] = []
        while i < len(line):
            ch = line[i]
            if ch == "%" and not escaped:
                # URLs often contain %2F-like escape sequences. Keep those.
                if i + 2 < len(line) and URL_PERCENT_ESCAPE_RE.match(line[i + 1 : i + 3]):
                    buf.append(ch)
                    i += 1
                    continue
                break
            buf.append(ch)
            escaped = ch == "\\" and not escaped
            if ch != "\\":
                escaped = False
            i += 1
        out_lines.append("".join(buf))
    return "\n".join(out_lines)


def _find_matching_brace(text: str, open_idx: int) -> int:
    depth = 0
    i = open_idx
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _strip_wrapping_braces(s: str) -> str:
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        return s[1:-1].strip()
    return s


def latex_to_text(text: str) -> str:
    if not text:
        return ""
    s = text
    s = re.sub(r"\\color\s*\{[^{}]*\}", "", s)
    for src, dst in LATEX_TEXT_REPLACEMENTS:
        s = s.replace(src, dst)
    s = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}", r"\2", s)
    s = s.replace("\\\\", "\n")
    s = s.replace(r"\>", " ")
    s = s.replace(r"\=", " ")
    s = s.replace("~", " ")
    s = s.replace(r"\&", "&")
    s = s.replace(r"\$", "$")
    s = re.sub(r"\$([^$]+)\$", r"\1", s)
    s = re.sub(r"([A-Za-z0-9])_\{([^{}]+)\}", r"\1_\2", s)
    s = re.sub(r"([A-Za-z0-9])\^\{([^{}]+)\}", r"\1^\2", s)
    s = s.replace(r"\_", "_")
    s = s.replace(r"\^", "^")
    s = s.replace(r"\bar", "bar ")
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    s = s.replace("{", " ").replace("}", " ")
    s = re.sub(r"\s+", " ", s).strip(" ,")
    return s


def extract_links(raw_latex: str) -> list[str]:
    links = re.findall(r"\\href\{([^}]*)\}\{[^}]*\}", raw_latex or "")
    return list(dict.fromkeys([u for u in links if u.startswith("http")]))


def extract_sections(tex_text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    starts: list[tuple[str, int, int]] = []
    marker = r"\resheading{"
    i = 0
    while True:
        idx = tex_text.find(marker, i)
        if idx == -1:
            break
        open_idx = tex_text.find("{", idx)
        if open_idx == -1:
            break
        close_idx = _find_matching_brace(tex_text, open_idx)
        if close_idx == -1:
            break
        heading_raw = tex_text[open_idx + 1 : close_idx]
        heading = latex_to_text(heading_raw)
        starts.append((heading, close_idx + 1, idx))
        i = close_idx + 1
    for n, (heading, content_start, _) in enumerate(starts):
        content_end = starts[n + 1][2] if n + 1 < len(starts) else len(tex_text)
        sections.append((heading, tex_text[content_start:content_end]))
    return sections


def section_content(sections: list[tuple[str, str]], key_substr: str) -> str:
    needle = key_substr.lower()
    for heading, content in sections:
        if needle in heading.lower():
            return content
    return ""


def extract_items(block: str) -> list[str]:
    items: list[str] = []
    cur: list[str] = []
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if re.match(r"^\s*\\item(?:\[\])?\s*", line):
            if cur:
                items.append("\n".join(cur).strip())
                cur = []
            line = re.sub(r"^\s*\\item(?:\[\])?\s*", "", line)
            cur.append(line)
        else:
            if cur:
                if re.match(r"^\s*\\end\{(itemize|enumerate|etaremune|tabbing)\}", line):
                    continue
                if re.match(r"^\s*\\begin\{(itemize|enumerate|etaremune|tabbing)\}", line):
                    continue
                cur.append(line)
    if cur:
        items.append("\n".join(cur).strip())
    return [it for it in items if it.strip()]


def extract_tabbing_lines(block: str) -> list[tuple[str, bool]]:
    body = re.sub(r"\\begin\{tabbing\}|\\end\{tabbing\}", "", block)
    chunks = body.split("\\\\")
    lines: list[tuple[str, bool]] = []
    for chunk in chunks:
        marker_chunk = chunk.replace(r"\>", " SEPSEP ")
        t = latex_to_text(marker_chunk).strip()
        if not t:
            continue
        if set(t) <= {"~", " "}:
            continue
        stripped = t.lstrip()
        is_cont = stripped.startswith("SEPSEP")
        line = t
        line = line.replace("~", " ").strip()
        line = line.replace("[]", " ").strip()
        if re.fullmatch(r"[\\\s.=:-]+", line or ""):
            continue
        line = line.replace("SEPSEP", " ").strip()
        line = re.sub(r"^\[+\]?$", "", line).strip()
        line = re.sub(r"^\s*=+\s*", "", line)
        if not line or line.lower() == "itemize":
            continue
        lines.append((line, is_cont))
    return lines


def group_tabbing_lines(lines: list[tuple[str, bool]], mode: str) -> list[str]:
    entries: list[str] = []
    current = ""
    for line, is_cont in lines:
        if mode == "flat":
            if current:
                entries.append(current)
            current = line
        else:
            if is_cont and current:
                current = f"{current} {line}".strip()
            else:
                if current:
                    entries.append(current)
                current = line
    if current:
        entries.append(current)

    seen: set[str] = set()
    out: list[str] = []
    for e in entries:
        e = re.sub(r"\s+", " ", e).strip(" ,")
        k = e.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def split_compound_service_entries(entries: list[str]) -> list[str]:
    role_start = (
        r"(?:Organizer|Organizing Committee|Convener|Chair|Panelist|Academic Committee|"
        r"Scientific Program|Committee|Local coordinator)"
    )
    out: list[str] = []
    for entry in entries:
        parts = re.split(rf"(?<!^)\s+(?={role_start}\s{{2,}})", entry)
        for p in parts:
            p = re.sub(r"\s+", " ", p).strip(" ,")
            if p:
                out.append(p)
    dedup: list[str] = []
    seen: set[str] = set()
    for x in out:
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append(x)
    return dedup


def split_cepc_series_entry(entry: str) -> list[str]:
    matches = list(re.finditer(r"CEPC\s*\(?(\d{4})\)?", entry))
    if len(matches) < 2:
        return [entry]

    head = entry[: matches[0].start()].strip(" ,")
    head = re.sub(r"\s+", " ", head)
    head = head.replace(
        "Scientific Program International Workshop on the Circular Electron-Positron Collider Committee",
        "Scientific Program Committee, International Workshop on the Circular Electron-Positron Collider",
    )
    head = head.replace("Committee", "Committee").strip(" ,")

    out: list[str] = []
    for i, m in enumerate(matches):
        year = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(entry)
        rest = re.sub(r"\s+", " ", entry[start:end]).strip(" ,")
        bullet = f"{head} CEPC {year}".strip()
        if rest:
            bullet = f"{bullet}, {rest}"
        out.append(bullet)
    return out


def polish_service_entries(entries: list[str]) -> list[str]:
    expanded: list[str] = []
    for entry in entries:
        expanded.extend(split_cepc_series_entry(entry))

    contextualized: list[str] = []
    cepc_context = ""
    for entry in expanded:
        norm = re.sub(r"\s+", " ", entry).strip(" ,")
        if not norm:
            continue
        if norm.startswith("Scientific Program International Workshop on the Circular Electron-Positron Collider"):
            cepc_context = "Scientific Program Committee, International Workshop on the Circular Electron-Positron Collider"
            continue
        if cepc_context and norm.startswith("Committee CEPC "):
            norm = f"{cepc_context}, {norm[len('Committee '):]}"
        contextualized.append(norm)

    out: list[str] = []
    seen: set[str] = set()
    for e in contextualized:
        e = re.sub(r"\s+", " ", e).strip(" ,")
        if not e:
            continue
        k = e.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def enforce_uniform_service_entry(entry: str) -> str:
    text = re.sub(r"\s+", " ", entry).strip(" ,")
    if not text:
        return text

    role = ""
    for candidate in sorted(ROLE_PREFIXES, key=len, reverse=True):
        m = re.match(rf"^{re.escape(candidate)}(?:,|\s+)?(.*)$", text)
        if m:
            role = candidate
            text = m.group(1).strip(" ,")
            break

    date = ""
    m = DATE_TAIL_RE.search(text)
    if m:
        date = m.group(1).strip(" ,")
        text = text[: m.start()].strip(" ,")

    if role and text and date:
        return f"{role}, {text}, {date}"
    if role and text:
        return f"{role}, {text}"
    if role and date:
        return f"{role}, {date}"
    if date and text:
        return f"{text}, {date}"
    return text or role


def enforce_uniform_service_format(entries: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        formatted = enforce_uniform_service_entry(entry)
        if not formatted:
            continue
        key = formatted.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(formatted)
    return out


def build_publication_items(items: list[str], list_id: str, source: str) -> list[dict]:
    pubs: list[dict] = []
    for idx, item in enumerate(items, start=1):
        links = extract_links(item)
        text = latex_to_text(item)
        title = infer_title(text)
        year = extract_year(text) or 1900
        arxiv = extract_arxiv(text, links)
        doi = extract_doi(text, links)
        journal_url = ""
        for link in links:
            if "arxiv.org" in link:
                continue
            if "doi.org" in link or "dx.doi.org" in link:
                continue
            journal_url = link
            break
        pubs.append(
            {
                "id": f"pub-{list_id}-{idx:03d}-{slugify(title)}",
                "title": title,
                "year": year,
                "date": publication_date(year, arxiv, text),
                "authors": "",
                "venue": infer_venue(text, title),
                "doi": doi,
                "arxiv": arxiv,
                "journal_url": journal_url,
                "section": PUB_SECTION_MAP.get(list_id, "other"),
                "featured": False,
                "source": source,
                "raw_text": text,
            }
        )
    return pubs


def split_title_event_for_lecture(text: str) -> tuple[str, str]:
    markers = [
        "Fudan Particle Physics Summer School",
        "Summer Institute",
        "Summer School",
        "Winter School",
        "TASI ",
        "KEK-PH",
    ]
    at = -1
    for marker in markers:
        idx = text.find(marker)
        if idx > 0 and (at < 0 or idx < at):
            at = idx
    if at > 0:
        return text[:at].strip(" ,"), text[at:].strip(" ,")
    if "," in text:
        left, right = text.split(",", 1)
        return left.strip(), right.strip()
    return text.strip(), ""


def build_talk_items(items: list[str], list_id: str, source: str) -> list[dict]:
    talks: list[dict] = []
    for idx, item in enumerate(items, start=1):
        links = extract_links(item)
        text = latex_to_text(item)
        title = infer_title(text)
        year = extract_year(text) or 1900
        talks.append(
            {
                "id": f"talk-{list_id}-{idx:03d}-{slugify(title)}",
                "title": title,
                "year": year,
                "date": talk_date(year, text),
                "event": infer_venue(text, title),
                "host": infer_host(infer_venue(text, title)),
                "location": "",
                "talk_type": infer_talk_type(text),
                "slides_url": next(
                    (u for u in links if "indico" in u or "slides" in u or "pdf" in u),
                    "",
                ),
                "video_url": next(
                    (u for u in links if "youtube.com" in u or "youtu.be" in u or "video" in u),
                    "",
                ),
                "source": source,
                "raw_text": text,
            }
        )
    return talks


def build_summer_lecture_talks(items: list[str], source: str) -> list[dict]:
    talks: list[dict] = []
    for idx, item in enumerate(items, start=1):
        links = extract_links(item)
        text = latex_to_text(item)
        title, event = split_title_event_for_lecture(text)
        year = extract_year(text) or 1900
        talks.append(
            {
                "id": f"talk-lecture-sw-{idx:03d}-{slugify(title)}",
                "title": title,
                "year": year,
                "date": talk_date(year, text),
                "event": event,
                "host": infer_host(event),
                "location": "",
                "talk_type": infer_talk_type(text),
                "slides_url": next(
                    (u for u in links if "indico" in u or "slides" in u or "pdf" in u),
                    "",
                ),
                "video_url": next(
                    (u for u in links if "youtube.com" in u or "youtu.be" in u or "video" in u),
                    "",
                ),
                "source": source,
                "raw_text": text,
            }
        )
    return talks


def parse_service_from_tex_sections(sections: list[tuple[str, str]]) -> dict:
    def tab(section_name: str, mode: str = "continuation") -> list[str]:
        return group_tabbing_lines(extract_tabbing_lines(section_content(sections, section_name)), mode)

    service = {
        "workshops": split_compound_service_entries(
            tab("Program&Workshop organizations", "continuation")
        ),
        "conference_sessions": split_compound_service_entries(
            tab("Conference&Workshop session organizations", "continuation")
        ),
        "committee_membership": split_compound_service_entries(
            tab("Committee and Membership", "continuation")
        ),
        "editorial_referee": tab("Journal Services", "flat"),
        "referee_services": tab("Other Referee Services", "flat"),
        "grant_review": tab("Grant (proposal) Review", "flat"),
        "university_service": tab("Departmental Service", "flat"),
    }
    referee_lines = tab("Journal Referee Services", "flat")
    blob = " ".join(referee_lines)
    journals = [
        latex_to_text(name).rstrip(" ,.;")
        for name in REFEREE_JOURNAL_RE.findall(blob)
        if latex_to_text(name).strip()
    ]
    dedup: list[str] = []
    seen: set[str] = set()
    for j in journals:
        k = j.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append(j)
    service["referee_journals"] = dedup
    service["workshops"] = enforce_uniform_service_format(polish_service_entries(service["workshops"]))
    service["conference_sessions"] = enforce_uniform_service_format(
        polish_service_entries(service["conference_sessions"])
    )
    service["committee_membership"] = enforce_uniform_service_format(service["committee_membership"])
    service["editorial_referee"] = enforce_uniform_service_format(service["editorial_referee"])
    service["referee_services"] = enforce_uniform_service_format(service["referee_services"])
    service["grant_review"] = enforce_uniform_service_format(service["grant_review"])
    service["university_service"] = enforce_uniform_service_format(service["university_service"])
    service["university_service"] = normalize_university_service_entries(service["university_service"])
    return service


def parse_teaching_from_tex_sections(sections: list[tuple[str, str]]) -> dict:
    block = section_content(sections, "Teaching Experience")
    items = [latex_to_text(i) for i in extract_items(block)]
    courses: list[dict] = []
    for line in items:
        parts = re.split(r"(?=Physics\s+\d{4}[A-Z]?\s*,)", line)
        for p in parts:
            parsed = parse_teaching_course_entry(p)
            if parsed:
                courses.append(parsed)
    return {"courses_umn": merge_teaching_courses(courses)}


MENTOR_PERIOD_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?"
    r"\s*\d{4}\s*[-–—]{1,2}\s*(?:now|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s*\d{4}))",
    re.I,
)

INSTITUTION_ALIASES = {
    "u of minnesota, twin cities": "University of Minnesota",
    "u of minnesota, morris": "University of Minnesota, Morris",
    "u of chinese academy of sciences, ucas fellowship": "University of Chinese Academy of Sciences",
    "u of science and technology, china": "University of Science and Technology of China",
    "zhejiang u, china": "Zhejiang University",
    "fudan u, china": "Fudan University",
    "florida international u": "Florida International University",
    "appalachian state u": "Appalachian State University",
    "binghamton university": "Binghamton University",
    "umass amherst": "UMass Amherst",
}


def normalize_mentor_period(period: str) -> str:
    text = re.sub(r"\s+", " ", period or "").strip()
    text = re.sub(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.",
        r"\1",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s*[-–—]+\s*", "-", text)
    text = re.sub(r"\bnow\b", "present", text, flags=re.I)
    return text.strip()


def normalize_institution_name(raw: str) -> str:
    key = re.sub(r"\s+", " ", (raw or "").strip()).lower()
    if key in INSTITUTION_ALIASES:
        return INSTITUTION_ALIASES[key]
    return re.sub(r"\s+", " ", raw).strip()


def extract_paren_groups(text: str) -> tuple[list[str], str]:
    groups: list[str] = []
    rest = text.strip()
    while rest.startswith("("):
        depth = 0
        close_idx = -1
        for idx, ch in enumerate(rest):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    close_idx = idx
                    break
        if close_idx < 0:
            break
        groups.append(rest[1:close_idx].strip())
        rest = rest[close_idx + 1 :].strip()
    return groups, rest.lstrip(",").strip()


def classify_mentoring_section(line: str) -> str | None:
    lower = re.sub(r"\s+", " ", line).strip().lower().rstrip(":")
    if "visiting graduate" in lower:
        return "visiting_graduate"
    if "summer-research graduate" in lower or "summer research graduate" in lower:
        return "summer_graduate"
    if lower.startswith("graduate student"):
        return "graduate"
    if lower.startswith("undergraduate"):
        return "undergraduate"
    if lower.startswith("postdoc"):
        return "postdoc"
    return None


def should_skip_mentoring_line(line: str) -> bool:
    lower = line.lower()
    if "for theory group postdocs" in lower:
        return True
    return False


def parse_career_arrow(text: str) -> tuple[str, str]:
    line = re.sub(r"^\s*->\s*", "", text).strip()
    if not line:
        return "", ""
    lower = line.lower()
    if "supervisor:" in lower:
        return "", ""

    postdoc_match = re.match(r"Postdoc at (.+?)(?:,\s*(.+))?$", line, flags=re.I)
    if postdoc_match:
        place = postdoc_match.group(1).strip()
        details = (postdoc_match.group(2) or "").strip()
        short = place.split(",")[0].strip()
        if details:
            if re.search(r"\bstarting\b", details, flags=re.I):
                leaving = f"{short} (Postdoc, {re.sub(r'^starting\\s+', '', details, flags=re.I)})"
            elif re.match(r"[^,]+,\s*[^,]+,\s*\d{4}", details):
                leaving = short
            elif re.search(r"\d{4}", details):
                leaving = f"{short} ({details})"
            else:
                leaving = f"{short} ({details})"
        else:
            leaving = place
        return leaving, short

    postdoc_comma_match = re.match(r"Postdoc,?\s*(.+)$", line, flags=re.I)
    if postdoc_comma_match:
        rest = postdoc_comma_match.group(1).strip()
        short = rest.split(",")[0].strip()
        return f"{short} (Postdoc)", short

    prof_match = re.match(r"(Assistant Professor|Associate Professor|Professor),?\s*(.+)$", line, flags=re.I)
    if prof_match:
        role = prof_match.group(1).strip()
        rest = prof_match.group(2).strip()
        short = rest.split(",")[0].strip()
        return f"{short} ({role})", short

    program_match = re.match(r"(.+?)\s+Graduate Program(?:,\s*Supervisor:\s*(.+))?$", line, flags=re.I)
    if program_match:
        program = program_match.group(1).strip()
        return program, program.split(",")[0].strip()

    return "", ""


def polish_career_labels(leaving: str, current: str) -> tuple[str, str]:
    leaving = leaving.replace("Utah University", "University of Utah")
    current = current.replace("Utah University", "University of Utah")
    if current == "Fermilab/U Chicago":
        current = "Fermilab / University of Chicago"
    if leaving.startswith("Perimeter Institute"):
        leaving = "Perimeter Institute (Postdoc, Sept 2026)"
    if "Theory Division" in leaving and "Fermilab" in leaving:
        leaving = "Theory Division, Fermilab (Postdoc, 2026)"
    return leaving.strip(), current.strip()


def aggregate_career_arrows(arrows: list[str]) -> tuple[str, str]:
    leaving = ""
    current = ""
    last_role = ""
    for arrow in arrows:
        leave, curr = parse_career_arrow(arrow)
        if leave and not leaving:
            leaving = leave
        if curr:
            current = curr
        lower = arrow.lower()
        if "assistant professor" in lower:
            last_role = "assistant_professor"
        elif "postdoc" in lower:
            last_role = "postdoc"
    leaving, current = polish_career_labels(leaving, current)
    if last_role == "assistant_professor" and current and "(Assistant Professor)" not in current:
        current = f"{current} (Assistant Professor)"
    return leaving, current


def parse_mentoring_main_line(line: str) -> dict | None:
    period_match = MENTOR_PERIOD_RE.search(line)
    if not period_match:
        return None
    period = normalize_mentor_period(period_match.group(1))
    before_period = line[: period_match.start()].rstrip(" ,")
    groups, rest = extract_paren_groups(before_period)
    name = rest.strip()
    if not name:
        return None
    return {
        "name": name,
        "period": period,
        "groups": groups,
    }


def build_graduate_student_entry(parsed: dict, arrows: list[str], *, visiting: bool) -> dict:
    leaving, current = aggregate_career_arrows(arrows)
    if not current and re.search(r"\bpresent\b", parsed["period"], flags=re.I):
        current = "University of Minnesota"
    entry: dict[str, str] = {
        "name": parsed["name"],
        "profile_url": "",
        "umn_period": parsed["period"],
        "leaving_institution": leaving,
        "current_institution": current,
    }
    if visiting:
        entry["notes"] = "Visiting graduate student (UCAS fellowship)"
        if "fermilab" in current.lower():
            entry["leaving_institution"] = entry["leaving_institution"].replace(
                "Theory Division of Fermilab", "Theory Division, Fermilab"
            )
            entry["current_institution"] = "Fermilab"
    return {k: v for k, v in entry.items() if v or k in {"name", "profile_url", "umn_period"}}


def build_postdoc_entry(parsed: dict, arrows: list[str]) -> dict:
    leaving, current = aggregate_career_arrows(arrows)
    entry: dict[str, str] = {
        "name": parsed["name"],
        "profile_url": "",
        "umn_period": parsed["period"],
        "leaving_institution": leaving,
        "current_institution": current,
    }
    return {k: v for k, v in entry.items() if v or k in {"name", "profile_url", "umn_period"}}


def build_research_graduate_entry(parsed: dict) -> dict:
    groups = parsed.get("groups") or []
    institution = normalize_institution_name(groups[0]) if groups else "University of Minnesota"
    return {
        "name": parsed["name"],
        "institution": institution,
        "umn_period": parsed["period"],
    }


def build_research_undergraduate_entry(parsed: dict) -> dict:
    groups = parsed.get("groups") or []
    program = ""
    institution = ""
    for group in groups:
        lower = group.lower()
        if "nsf reu" in lower:
            program = "NSF REU"
        elif not institution:
            institution = normalize_institution_name(group)
    if not institution and groups:
        institution = normalize_institution_name(groups[-1])
    entry: dict[str, str] = {
        "name": parsed["name"],
        "institution": institution,
        "umn_period": parsed["period"],
    }
    if program:
        entry["program"] = program
    return entry


def parse_mentoring_from_tex_sections(sections: list[tuple[str, str]]) -> dict:
    block = section_content(sections, "Mentorship/Supervision")
    lines = [line for line, _ in extract_tabbing_lines(block)]

    mentoring: dict[str, list[dict]] = {
        "graduate_students": [],
        "postdocs": [],
        "research_graduates": [],
        "research_undergraduates": [],
    }
    section = ""
    pending: dict | None = None
    pending_arrows: list[str] = []

    def flush_pending() -> None:
        nonlocal pending, pending_arrows
        if not pending:
            pending_arrows = []
            return
        if section == "graduate":
            mentoring["graduate_students"].append(build_graduate_student_entry(pending, pending_arrows, visiting=False))
        elif section == "visiting_graduate":
            mentoring["graduate_students"].append(build_graduate_student_entry(pending, pending_arrows, visiting=True))
        elif section == "summer_graduate":
            mentoring["research_graduates"].append(build_research_graduate_entry(pending))
        elif section == "undergraduate":
            mentoring["research_undergraduates"].append(build_research_undergraduate_entry(pending))
        elif section == "postdoc":
            mentoring["postdocs"].append(build_postdoc_entry(pending, pending_arrows))
        pending = None
        pending_arrows = []

    for raw_line in lines:
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or should_skip_mentoring_line(line):
            continue

        section_match = classify_mentoring_section(line)
        if section_match:
            flush_pending()
            section = section_match
            continue

        if line.startswith("->"):
            if pending is not None:
                pending_arrows.append(line)
            continue

        if pending is not None and MENTOR_PERIOD_RE.search(line) and not classify_mentoring_section(line):
            flush_pending()

        parsed = parse_mentoring_main_line(line)
        if not parsed:
            continue
        pending = parsed
        pending_arrows = []

    flush_pending()
    return mentoring


def merge_mentoring_profile_urls(new_data: dict, old_data: dict) -> dict:
    for section in ("graduate_students", "postdocs", "research_graduates", "research_undergraduates"):
        old_items = {
            str(item.get("name") or "").lower(): item
            for item in (old_data.get(section) or [])
            if item.get("name")
        }
        for item in new_data.get(section) or []:
            name = str(item.get("name") or "").lower()
            old_item = old_items.get(name)
            if not old_item:
                continue
            profile_url = str(old_item.get("profile_url") or "").strip()
            if profile_url:
                item["profile_url"] = profile_url
    return new_data


def merge_lecture_talks(new_talks: list[dict], old_talks: list[dict]) -> tuple[list[dict], int]:
    def talk_key(talk: dict) -> tuple[str, str]:
        title_text = latex_to_text(str(talk.get("title") or "")).lower()
        title_text = re.split(r"\(remote\)|kek-ph lectures and workshops", title_text)[0]
        title = re.sub(r"[^a-z0-9]+", "", title_text)
        date = str(talk.get("date") or "")
        return title, date

    new_ids = {str(t.get("id") or "") for t in new_talks}
    new_keys = {talk_key(t) for t in new_talks}
    preserved: list[dict] = []
    for old in old_talks:
        old_id = str(old.get("id") or "")
        if old_id and old_id in new_ids:
            continue
        if talk_key(old) in new_keys:
            continue
        if old_id.startswith("talk-lecture-sw-"):
            continue
        if is_lecture_talk(old):
            preserved.append(old)
    merged = list(new_talks) + preserved
    merged.sort(
        key=lambda x: (
            str(x.get("date") or ""),
            int(x.get("year") or 0),
            str(x.get("title") or ""),
        ),
        reverse=True,
    )
    return merged, len(preserved)


def run_tex_pipeline(
    input_path: Path,
    pub_out: Path,
    talk_out: Path,
    service_out: Path,
    teaching_out: Path,
    mentoring_out: Path,
    hand_edits_path: Path,
    approve_conflicts: bool = False,
    conflict_report_path: Path | None = None,
    conflict_approvals_path: Path | None = None,
    approvals_template_path: Path | None = None,
) -> None:
    from clean_bibliography_data import normalize_publication, normalize_talk

    source = input_path.as_posix()
    tex = strip_tex_comments(input_path.read_text(encoding="utf-8", errors="ignore"))
    sections = extract_sections(tex)

    pub_l1 = build_publication_items(
        extract_items(section_content(sections, "Publications in Refereed Journals")),
        "l1",
        source,
    )
    pub_l2 = build_publication_items(
        extract_items(section_content(sections, "Other Publications (editor or co-editor)")),
        "l2",
        source,
    )
    pub_l3 = build_publication_items(
        extract_items(section_content(sections, "Other Publications (contributor or endorser)")),
        "l3",
        source,
    )
    publications = [normalize_publication(p) for p in (pub_l1 + pub_l2 + pub_l3)]
    publications.sort(key=lambda x: (x["year"], x["title"]), reverse=True)

    talks_sem = build_talk_items(extract_items(section_content(sections, "Seminar & Colloquium")), "l5", source)
    talks_wk = build_talk_items(
        extract_items(section_content(sections, "Workshop and Conference Talks")),
        "l6",
        source,
    )
    talks_lect = build_summer_lecture_talks(
        extract_items(section_content(sections, "Summer/Winter School Lectures")),
        source,
    )
    talks = [normalize_talk(t) for t in (talks_sem + talks_wk + talks_lect)]
    talks.sort(key=lambda x: (x["year"], x["title"]), reverse=True)

    service = parse_service_from_tex_sections(sections)
    teaching = parse_teaching_from_tex_sections(sections)
    mentoring = parse_mentoring_from_tex_sections(sections)

    old_pubs = load_yaml_list(pub_out)
    old_talks = load_yaml_list(talk_out)
    old_service = load_yaml_dict(service_out)
    old_teaching = load_yaml_dict(teaching_out)
    old_mentoring = load_yaml_dict(mentoring_out)

    root = Path(__file__).resolve().parent.parent
    apply_featured_flags(publications, root, pub_out)
    talks, preserved_count = merge_lecture_talks(talks, old_talks)
    mentoring = merge_mentoring_profile_urls(mentoring, old_mentoring)

    rerun_hint = (
        f"python scripts/parse_cv_html.py --conflict-approvals backups/cv-conflict-approvals.json"
        f" --input {input_path.as_posix()}"
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
        new_mentoring=mentoring,
        hand_edits_path=hand_edits_path,
        conflict_approvals_path=conflict_approvals_path,
        approve_conflicts=approve_conflicts,
        conflict_report_path=conflict_report_path,
        approvals_template_path=approvals_template_path,
        rerun_hint=rerun_hint,
    )
    publications = resolved["publications"]
    talks = resolved["talks"]
    service = resolved["service"]
    teaching = resolved["teaching"]
    mentoring = resolved["mentoring"]

    pub_out.parent.mkdir(parents=True, exist_ok=True)
    talk_out.parent.mkdir(parents=True, exist_ok=True)
    service_out.parent.mkdir(parents=True, exist_ok=True)
    teaching_out.parent.mkdir(parents=True, exist_ok=True)
    mentoring_out.parent.mkdir(parents=True, exist_ok=True)

    pub_out.write_text(yaml.safe_dump(publications, sort_keys=False, allow_unicode=True), encoding="utf-8")
    talk_out.write_text(yaml.safe_dump(talks, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if any(service.get(k) for k in service):
        service_out.write_text(yaml.safe_dump(service, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if any(teaching.get(k) for k in teaching):
        teaching_out.write_text(yaml.safe_dump(teaching, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if any(mentoring.get(k) for k in mentoring):
        mentoring_out.write_text(yaml.safe_dump(mentoring, sort_keys=False, allow_unicode=True), encoding="utf-8")

    print(f"Parsed CV TeX: {source}")
    print(f"Wrote {len(publications)} publication entries to {pub_out}")
    print(f"Wrote {len(talks)} talk entries to {talk_out}")
    print(f"Extracted {len(talks_lect)} summer/winter school lecture entries.")
    if any(service.get(k) for k in service):
        print(f"Wrote service entries to {service_out}")
        print(f"Extracted {len(service.get('referee_journals', []))} refereed journals.")
    if any(teaching.get(k) for k in teaching):
        print(f"Wrote teaching entries to {teaching_out}")
    if any(mentoring.get(k) for k in mentoring):
        print(f"Wrote mentoring entries to {mentoring_out}")
        print(
            "Mentoring counts:"
            f" graduate_students={len(mentoring.get('graduate_students', []))},"
            f" postdocs={len(mentoring.get('postdocs', []))},"
            f" research_graduates={len(mentoring.get('research_graduates', []))},"
            f" research_undergraduates={len(mentoring.get('research_undergraduates', []))}"
        )
    if preserved_count:
        print(f"Preserved {preserved_count} legacy lecture entries missing from current TeX import.")
    summarize_changes("Publication import", old_pubs, publications)
    summarize_changes("Talk import", old_talks, talks)

