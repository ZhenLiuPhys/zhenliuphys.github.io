#!/usr/bin/env python3
"""Generate local career trajectory figures (not for website)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TRAJECTORY_DIR = Path(__file__).resolve().parent
ROOT = TRAJECTORY_DIR.parent
if str(TRAJECTORY_DIR) not in sys.path:
    sys.path.insert(0, str(TRAJECTORY_DIR))

from trajectory_lib.fetch_inspire_citations import (
    ensure_citations,
    citation_series_from_cache,
    load_cache,
    list_snapshots,
    load_snapshot,
    growth_series,
    write_growth_summary_csv,
    print_citation_history,
)
from trajectory_lib.citation_exclusions import (
    load_exclusions,
    build_citation_inventory,
    write_citation_inventory_csv,
    print_citation_summary,
)
from trajectory_lib.load_data import (
    load_publications,
    load_talks,
    load_service,
    publication_series,
    talk_series,
    refereed_publications,
    year_range_from_series,
)
from trajectory_lib.parse_service import service_series
from trajectory_lib.parse_letters import (
    load_recommendation_letters,
    letter_series,
    letter_series_grouped,
    letter_detail_rows,
    write_letters_detail_csv,
    print_letters_summary,
)
from trajectory_lib.plots import (
    plot_multi_series,
    plot_letters_annual_stacked,
    plot_citations_by_pub_year,
    plot_citations_cumulative_stock,
    plot_citations_growth_total,
    plot_citations_growth_delta,
    plot_citations_growth_decomposition,
    plot_citations_growth_by_cohort,
    write_summary_csv,
    SERIES_ORDER,
    today_iso,
)


def spot_check(pubs, talks) -> None:
    pub_s = publication_series(pubs)
    talk_s = talk_series(talks)
    for year in (2024, 2023):
        ref = pub_s["Refereed"].get(year, 0)
        ed = pub_s["Editor"].get(year, 0)
        ct = pub_s["Contributor"].get(year, 0)
        talks_n = talk_s["Total"].get(year, 0)
        print(f"spot-check {year}: refereed={ref} editor={ed} contributor={ct} talks={talks_n}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Career trajectory figures (local).")
    parser.add_argument("--all", action="store_true", help="Pubs, talks, service, and citations")
    parser.add_argument("--pubs", action="store_true")
    parser.add_argument("--talks", action="store_true")
    parser.add_argument("--service", action="store_true")
    parser.add_argument("--letters", action="store_true", help="Recommendation letter plots (local YAML)")
    parser.add_argument("--citations", action="store_true", help="Fetch inSPIRE + citation plots (network)")
    parser.add_argument("--refresh-citations", action="store_true", help="Re-fetch all inSPIRE counts")
    parser.add_argument("--list-citations", action="store_true", help="Print citation inventory and write citations_inventory.csv")
    parser.add_argument(
        "--list-citation-history",
        action="store_true",
        help="Print archived snapshot dates and totals",
    )
    parser.add_argument("--spot-check", action="store_true")
    args = parser.parse_args()

    if args.list_citation_history:
        exclusions = load_exclusions(ROOT)
        print_citation_history(ROOT, exclusions)
        return

    if not any([args.all, args.pubs, args.talks, args.service, args.letters, args.citations, args.list_citations]):
        args.pubs = args.talks = args.service = True

    if args.list_citations and not any([args.all, args.pubs, args.talks, args.service, args.citations]):
        pubs = load_publications(ROOT)
        out_dir = TRAJECTORY_DIR / "output"
        refereed = refereed_publications(pubs)
        cache = load_cache(ROOT)
        if not cache.get("papers"):
            cache = ensure_citations(refereed, ROOT, refresh=False)
        exclusions = load_exclusions(ROOT)
        inventory = build_citation_inventory(ROOT, cache, exclusions)
        write_citation_inventory_csv(inventory, out_dir / "citations_inventory.csv")
        print_citation_summary(inventory)
        print(f"\nWrote {out_dir / 'citations_inventory.csv'}")
        print("Exclude papers: edit trajectory/citation_exclusions.yaml (arxiv IDs), then --citations")
        return

    out_dir = TRAJECTORY_DIR / "output"
    pubs = load_publications(ROOT)
    talks = load_talks(ROOT)
    service = load_service(ROOT)

    pub_s = publication_series(pubs)
    talk_s = talk_series(talks)
    svc_s, svc_notes = service_series(service, ROOT)

    if args.spot_check:
        spot_check(pubs, talks)

    years = year_range_from_series([pub_s, talk_s, svc_s])

    summary_tables: dict[str, dict[str, dict[int, int]]] = {}

    if args.all or args.pubs:
        plot_multi_series(
            years, pub_s, order=SERIES_ORDER["pubs"],
            title="Publications", ylabel="Count", root=ROOT,
            out_path=out_dir / "pubs_annual.png", cumulative_mode=False,
        )
        plot_multi_series(
            years, pub_s, order=SERIES_ORDER["pubs"],
            title="Publications", ylabel="Cumulative count", root=ROOT,
            out_path=out_dir / "pubs_cumulative.png", cumulative_mode=True,
        )
        summary_tables["pubs"] = {k: v for k, v in pub_s.items() if k != "Total"}
        print("Wrote pubs_annual.png, pubs_cumulative.png")

    if args.all or args.talks:
        plot_multi_series(
            years, talk_s, order=SERIES_ORDER["talks"],
            title="Talks", ylabel="Count", root=ROOT,
            out_path=out_dir / "talks_annual.png", cumulative_mode=False,
        )
        plot_multi_series(
            years, talk_s, order=SERIES_ORDER["talks"],
            title="Talks", ylabel="Cumulative count", root=ROOT,
            out_path=out_dir / "talks_cumulative.png", cumulative_mode=True,
        )
        summary_tables["talks"] = {k: v for k, v in talk_s.items() if k != "Total"}
        print("Wrote talks_annual.png, talks_cumulative.png")

    if args.all or args.service:
        for note in svc_notes:
            print(f"service note: {note}")
        plot_multi_series(
            years, svc_s, order=SERIES_ORDER["service"],
            title="Service (organization & chairing)", ylabel="Count", root=ROOT,
            out_path=out_dir / "service_annual.png", cumulative_mode=False,
        )
        plot_multi_series(
            years, svc_s, order=SERIES_ORDER["service"],
            title="Service (organization & chairing)", ylabel="Cumulative count", root=ROOT,
            out_path=out_dir / "service_cumulative.png", cumulative_mode=True,
        )
        summary_tables["service"] = {k: v for k, v in svc_s.items() if k != "Total"}
        print("Wrote service_annual.png, service_cumulative.png")

    if args.all or args.letters:
        try:
            letter_data = load_recommendation_letters(ROOT)
        except (FileNotFoundError, ValueError) as exc:
            print(f"letters skipped: {exc}")
        else:
            letter_rows = letter_detail_rows(letter_data)
            letter_fine = letter_series(letter_data)
            letter_s = letter_series_grouped(letter_data)
            letter_years = year_range_from_series([letter_s], xmin=2010)
            print_letters_summary(letter_rows, letter_s, fine_series=letter_fine)
            plot_letters_annual_stacked(
                letter_years,
                letter_s,
                order=SERIES_ORDER["letters"],
                root=ROOT,
                out_path=out_dir / "letters_annual.png",
            )
            plot_multi_series(
                letter_years,
                letter_s,
                order=SERIES_ORDER["letters"],
                title="Recommendation letters",
                ylabel="Cumulative count",
                root=ROOT,
                out_path=out_dir / "letters_cumulative.png",
                cumulative_mode=True,
            )
            write_letters_detail_csv(letter_rows, out_dir / "letters_detail.csv")
            summary_tables["letters"] = {k: v for k, v in letter_s.items() if k != "Total"}
            print("Wrote letters_annual.png, letters_cumulative.png, letters_detail.csv")

    if args.list_citations:
        refereed = refereed_publications(pubs)
        cache = load_cache(ROOT)
        if not (cache.get("papers") and not args.refresh_citations):
            cache = ensure_citations(refereed, ROOT, refresh=args.refresh_citations)
        exclusions = load_exclusions(ROOT)
        inventory = build_citation_inventory(ROOT, cache, exclusions)
        write_citation_inventory_csv(inventory, out_dir / "citations_inventory.csv")
        print_citation_summary(inventory)
        print(f"\nWrote {out_dir / 'citations_inventory.csv'}")

    if args.all or args.citations:
        refereed = refereed_publications(pubs)
        exclusions = load_exclusions(ROOT)
        cache = ensure_citations(refereed, ROOT, refresh=args.refresh_citations)
        inventory = build_citation_inventory(ROOT, cache, exclusions)
        by_year, stock = citation_series_from_cache(cache, refereed, exclusions=exclusions)
        snap = cache.get("fetched") or today_iso()
        cite_years = year_range_from_series([{"c": by_year}])
        suffix = f", {len(exclusions)} excluded" if exclusions else ""
        plot_citations_by_pub_year(
            cite_years,
            by_year,
            ROOT,
            out_dir / "citations_by_pub_year.png",
            f"{snap}{suffix}",
        )
        plot_citations_cumulative_stock(
            cite_years,
            stock,
            ROOT,
            out_dir / "citations_cumulative_stock.png",
            f"{snap}{suffix}",
        )
        write_citation_inventory_csv(inventory, out_dir / "citations_inventory.csv")
        summary_tables["citations_annual"] = {"refereed_citations": by_year}
        n_in = sum(1 for r in inventory if not r["excluded"])
        print(f"Wrote citation figures (snapshot {snap}, {n_in}/{len(refereed)} papers counted{suffix})")

        snap_paths = list_snapshots(ROOT)
        if len(snap_paths) >= 2:
            snaps = [load_snapshot(p) for p in snap_paths]
            growth = growth_series(snaps, exclusions)
            write_growth_summary_csv(growth["summary_rows"], out_dir / "citations_growth_summary.csv")
            plot_citations_growth_total(growth["summary_rows"], out_dir / "citations_growth_total.png")
            plot_citations_growth_delta(growth["summary_rows"], out_dir / "citations_growth_delta.png")
            plot_citations_growth_decomposition(
                growth["latest_paper_deltas"],
                growth["latest_interval"],
                out_dir / "citations_growth_decomposition.png",
            )
            plot_citations_growth_by_cohort(
                growth["latest_cohort_deltas"],
                growth["latest_interval"],
                out_dir / "citations_growth_by_cohort.png",
            )
            interval = growth["latest_interval"]
            span = f"{interval[0]} → {interval[1]}" if interval else "n/a"
            print(
                f"Wrote citation growth figures ({len(snap_paths)} snapshots; latest interval {span})"
            )
        else:
            print(
                "Citation growth plots skipped "
                f"({len(snap_paths)} snapshot(s) in trajectory/citations_history/; need ≥2)"
            )

    if summary_tables:
        write_summary_csv(years, summary_tables, out_dir / "summary_table.csv")
        print("Wrote summary_table.csv")


if __name__ == "__main__":
    main()
