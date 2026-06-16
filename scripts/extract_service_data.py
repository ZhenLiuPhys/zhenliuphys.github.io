#!/usr/bin/env python3
"""Extract professional service data from CV source into data/source/service.yaml."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from parse_cv_html import DEFAULT_CV_INPUT, parse_service_data, resolve_cv_input
from parse_cv_tex import extract_sections, parse_service_from_tex_sections, strip_tex_comments


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract service data from TeX-first CV source.")
    parser.add_argument(
        "--input",
        default=DEFAULT_CV_INPUT,
        help="CV source path (default: Material/ZhenLiu_CV.tex)",
    )
    parser.add_argument("--output", default="data/source/service.yaml")
    args = parser.parse_args()

    input_path = resolve_cv_input(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = input_path.suffix.lower()
    if suffix == ".tex":
        tex_text = input_path.read_text(encoding="utf-8", errors="ignore")
        sections = extract_sections(strip_tex_comments(tex_text))
        service = parse_service_from_tex_sections(sections)
        print(f"Parsed CV TeX: {input_path.as_posix()}")
    elif suffix in {".htm", ".html"}:
        html_text = input_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html_text, "html.parser")
        service = parse_service_data(soup)
        print(f"Parsed CV HTML: {input_path.as_posix()}")
    else:
        raise SystemExit(
            f"Unsupported CV input format: {input_path.as_posix()} (allowed: .tex, .htm, .html)"
        )

    if any(service.get(k) for k in service):
        output_path.write_text(
            yaml.safe_dump(service, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"Wrote service entries to {output_path}")
        print(f"Extracted {len(service.get('referee_journals', []))} refereed journals.")
    else:
        print("No service sections detected; no output written.")


if __name__ == "__main__":
    main()
