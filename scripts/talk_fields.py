"""Parse talk venue, location, and dates from CV-import event strings."""

from __future__ import annotations

import re

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

MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)

MONTH_YEAR_RE = re.compile(
    rf"\b({MONTH_NAMES})\.?\s*((?:19|20)\d{{2}})\b",
    re.I,
)

REMOTE_RE = re.compile(r"^\(remote\)\s*", re.I)
LINK_RE = re.compile(r"\(\s*link\s*\)|\[\s*link\s*\]", re.I)

EVENT_PREFIX_RE = re.compile(
    r"^(?:\(scheduled\)\s*)?"
    r"(?:"
    r"(?:invited|contributed)\s+(?:plenary\s+)?talk at\s+"
    r"|(?:invited|contributed)\s+plenary\s+talk\s+at\s+"
    r"|parallel talk at\s+"
    r"|plenary talk at\s+"
    r"|talk at\s+"
    r"|seminar at\s+"
    r"|colloquium at\s+"
    r"|theory seminar at\s+"
    r")",
    re.I,
)

TITLE_SPLIT_RE = re.compile(
    r",\s*(?:(?:\(scheduled\)\s*)?"
    r"(?:(?:invited|contributed)\s+)?"
    r"(?:parallel talk at\b|plenary talk at\b|talk at\b|"
    r"(?:[A-Za-z0-9/&\-\.\s]+\s+)?seminar,\s*|"
    r"colloquium,\s*)"
    r")",
    re.I,
)

LECTURE_KEYWORD_RE = re.compile(
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

US_STATES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
    "district of columbia",
}

INSTITUTION_HINTS = (
    "university",
    "institute",
    "institution",
    "laboratory",
    "laboratories",
    "lab",
    "fermilab",
    "cern",
    "fnal",
    "slac",
    "ihep",
    "kitp",
    "cnrs",
    "osu",
    "uw-",
    "mit",
    "caltech",
    "college",
    "school of",
    "department",
    "pacc",
    "center for",
    "centre for",
)

COUNTRIES = {
    "usa",
    "u.s.a.",
    "us",
    "u.s.",
    "united states",
    "china",
    "japan",
    "canada",
    "germany",
    "france",
    "switzerland",
    "italy",
    "uk",
    "u.k.",
    "united kingdom",
    "australia",
    "korea",
    "south korea",
    "taiwan",
    "india",
    "israel",
    "spain",
    "sweden",
    "netherlands",
    "austria",
}


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = LINK_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.-")
    return text


def month_token_to_num(token: str) -> int | None:
    return MONTH_MAP.get(token.lower().rstrip("."))


def format_date_display(year: int, month: int | None) -> str:
    names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    if month and 1 <= month <= 12:
        return f"{names[month]} {year}"
    return str(year)


def build_iso_date(year: int, month: int | None) -> str:
    y = year if year and year > 0 else 1900
    m = month if month and 1 <= month <= 12 else 1
    return f"{y:04d}-{m:02d}-01"


def extract_dates(text: str) -> tuple[list[tuple[int, int, str]], str]:
    """Return [(year, month, matched_span)], remainder with date chunks removed."""
    matches: list[tuple[int, int, str]] = []
    for m in MONTH_YEAR_RE.finditer(text):
        month = month_token_to_num(m.group(1))
        year = int(m.group(2))
        if month:
            matches.append((year, month, m.group(0)))
    if not matches:
        return [], text
    # Prefer the last plausible date (CV often duplicates).
    year, month, _ = matches[-1]
    remainder = MONTH_YEAR_RE.sub("", text)
    remainder = re.sub(r",\s*,", ",", remainder).strip(" ,.-")
    return [(year, month, "")], remainder


def is_us_state(token: str) -> bool:
    t = token.strip()
    if re.fullmatch(r"[A-Z]{2}", t):
        return True
    return t.lower() in US_STATES


def is_country(token: str) -> bool:
    return token.strip().lower().rstrip(".") in COUNTRIES


def is_institution(chunk: str) -> bool:
    lower = chunk.lower()
    return any(h in lower for h in INSTITUTION_HINTS)


def split_parts(text: str) -> list[str]:
    return [p.strip() for p in text.split(",") if p.strip()]


def parse_location_from_parts(parts: list[str]) -> tuple[str, list[str]]:
    if not parts:
        return "", parts
    if len(parts) == 2 and is_us_state(parts[-1]):
        return parts[-1], [parts[0]]
    if len(parts) >= 2 and is_us_state(parts[-1]):
        loc = f"{parts[-2]}, {parts[-1]}"
        return loc, parts[:-2]
    if len(parts) >= 2 and is_country(parts[-1]):
        loc = f"{parts[-2]}, {parts[-1]}"
        return loc, parts[:-2]
    if len(parts) >= 3 and is_us_state(parts[-2]) and len(parts[-1]) <= 20:
        # City, State, Country rare — treat last two as location
        loc = ", ".join(parts[-2:])
        return loc, parts[:-2]
    return "", parts


def assign_venue_institution(parts: list[str]) -> tuple[str, str]:
    if not parts:
        return "", ""
    if len(parts) == 1:
        chunk = parts[0]
        if is_institution(chunk):
            return "", chunk
        return chunk, ""
    institution = ""
    venue_parts: list[str] = []
    for chunk in parts:
        if is_institution(chunk) and not venue_parts:
            institution = chunk
        elif is_institution(chunk) and venue_parts:
            institution = chunk
        else:
            venue_parts.append(chunk)
    venue = ", ".join(venue_parts).strip()
    if not venue and institution:
        venue, institution = institution, ""
    return venue, institution


def strip_event_prefix(text: str) -> str:
    text = clean_text(text)
    text = REMOTE_RE.sub("", text)
    text = EVENT_PREFIX_RE.sub("", text, count=1)
    return text.strip(" ,.-")


def clean_talk_title(title: str, raw_text: str = "") -> str:
    title = clean_text(title)
    source = raw_text or title or ""
    needs_split = bool(
        re.search(
            r",\s*(?:parallel|plenary)\s+talk\b|\btalk at\b|,\s*[^,]+\s+seminar,\s*",
            title,
            re.I,
        )
    )
    if needs_split or not title:
        m = TITLE_SPLIT_RE.search(source)
        if m:
            return clean_text(source[: m.start()])
    return title


def infer_talk_type(text: str) -> str:
    lower = text.lower()
    if "contributed" in lower:
        return "contributed"
    if "invited" in lower or "plenary" in lower:
        return "invited"
    if "seminar" in lower or "colloquium" in lower:
        return "seminar"
    if "parallel" in lower:
        return "contributed"
    return "talk"


WORKSHOP_HINTS = (
    "workshop",
    "conference",
    "symposium",
    "meeting",
    "forum",
    "snowmass",
    "school",
    "pheno",
    "moriond",
    "aspen",
    "taofest",
    "dpf",
    "parallel talk",
    "winter institute",
    "program",
    "festival",
    "cetup",
    "pascos",
    "susy ",
    "cepc20",
    "hdays",
    "h days",
    "fpc ",
    "lpc ",
    "energy frontier",
    "lightning talk",
    "mepa",
    "supercollider",
    "lhcp",
    "lcws",
)

PARALLEL_OR_SESSION_RE = re.compile(
    r"\b(?:contributed\s+)?parallel\s+talk\b|"
    r"\bparallel\s+session\b|"
    r"\bsession of\b|"
    r"\b\w[\w\s-]{0,40}\s+session of\b",
    re.I,
)

MAIN_PLENARY_VENUE_RE = re.compile(
    r"^(?:"
    r"pheno(?:-dpf)?\s*20\d{2}|"
    r"phenomenology symposium \(pheno20\d{2}\)|"
    r"lepton photon(?:\s+conference)?|"
    r"cepc20\d{2}|"
    r"tevpa\s*20\d{2}\s+conference|"
    r"dpf meeting|"
    r"aps dpf"
    r")$",
    re.I,
)


def _is_subordinate_conference_talk(text: str) -> bool:
    return bool(PARALLEL_OR_SESSION_RE.search(text))


def _is_major_conference_plenary(venue: str, text: str) -> bool:
    if _is_subordinate_conference_talk(text):
        return False
    venue_key = (venue or "").strip().lower()
    if venue_key and MAIN_PLENARY_VENUE_RE.match(venue_key):
        return True
    # Pheno / CEPC listed as leading event fragment without parallel/session wording.
    if re.search(
        r"(?:^|[,(]\s*)(?:pheno(?:-dpf)?\s*20\d{2}|cepc20\d{2}|lepton photon(?:\s+conference)?)\b",
        text,
        re.I,
    ) and not _is_subordinate_conference_talk(text):
        if re.search(r"\b(?:parallel|session of|contributed)\b", text, re.I):
            return False
        return True
    return False


def infer_talk_category(combined: str, title: str, venue: str, host: str) -> str:
    text = " ".join(
        part for part in (combined, title, venue, host) if part
    ).lower()
    text = re.sub(r"\(scheduled\)\s*", "", text)
    text = re.sub(r"\bscheduled\b", "", text)
    if LECTURE_KEYWORD_RE.search(text):
        return "lecture"
    if re.search(r"\b(?:invited\s+)?plenary\b|\bkeynote\b", text):
        return "plenary"
    if _is_major_conference_plenary(venue, text):
        return "plenary"
    if "colloquium" in text or "coffee hour" in text:
        return "colloquium"
    if "seminar" in text:
        return "seminar"
    if any(k in text for k in WORKSHOP_HINTS):
        return "workshop"
    if re.search(
        r"\binvited\s+(?:(?:review|overview|theory\s+overview)\s+)?talk\s+(?:at|in)\b",
        text,
    ):
        return "workshop"
    if is_institution(venue) or is_institution(host):
        return "seminar"
    lead = combined.split(",")[0].strip() if combined else ""
    if lead and is_institution(lead):
        return "seminar"
    return "other"


def parse_talk_fields(talk: dict) -> dict:
    """Populate venue, host, location, date, date_display, event_display from event/raw text."""
    raw = talk.get("raw_text") or ""
    event = (talk.get("event") or "").strip()
    if not event:
        event = (talk.get("event_display") or "").strip()
    combined = event or raw

    title = clean_talk_title(talk.get("title", ""), raw)
    talk["title"] = title

    if raw and title:
        m = re.search(re.escape(title), raw, re.I)
        if m:
            tail = clean_text(raw[m.end() :])
            if tail and (not event or len(tail) > len(event) * 0.8):
                combined = tail

    core = strip_event_prefix(combined)
    dates, core = extract_dates(core)
    year = talk.get("year") or 1900
    month: int | None = None
    if dates:
        year, month, _ = dates[-1]
    elif talk.get("date"):
        try:
            parts = str(talk["date"]).split("-")
            year = int(parts[0])
            if len(parts) >= 2:
                month = int(parts[1])
        except (ValueError, IndexError):
            pass

    parts = split_parts(core)
    location, parts = parse_location_from_parts(parts)
    venue, institution = assign_venue_institution(parts)

    if not location and talk.get("location"):
        location = clean_text(talk["location"])
    old_host = clean_text(talk.get("host", ""))
    if not institution and old_host and is_institution(old_host):
        institution = old_host
    if not venue and institution and "seminar" in institution.lower():
        venue = institution
        institution = ""

    talk["year"] = int(year)
    talk["date"] = build_iso_date(int(year), month)
    talk["date_display"] = format_date_display(int(year), month)
    talk["venue"] = venue
    talk["host"] = institution
    talk["location"] = location
    talk["talk_type"] = infer_talk_type(combined)
    talk["category"] = infer_talk_category(combined, title, venue, institution)
    sched_blob = f"{title} {combined}"
    talk["scheduled"] = bool(re.search(r"\(scheduled\)|\bscheduled\b", sched_blob, re.I))

    # Compact line for templates / search
    bits: list[str] = []
    if venue:
        bits.append(venue)
    elif institution:
        bits.append(institution)
    if location:
        bits.append(location)
    if month:
        bits.append(talk["date_display"])
    talk["event_display"] = " · ".join(bits)

    talk["placeholder"] = title.lower() in {"tbd", "(scheduled) tbd"} or title.lower().startswith(
        "tbd "
    )
    return talk
