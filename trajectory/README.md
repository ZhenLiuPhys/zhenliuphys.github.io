# Career trajectory figures (local)

Personal reflection plots from site YAML — **not** published on zhenliu.net.

## Quick start

```bash
pip install -r requirements.txt
.venv/bin/python trajectory/plot_trajectory.py --all --spot-check
```

Phase 1–2 (no network): pubs, talks, service + `summary_table.csv`.

Citations (inSPIRE, refereed only):

```bash
.venv/bin/python trajectory/plot_trajectory.py --citations
.venv/bin/python trajectory/plot_trajectory.py --citations --refresh-citations
```

Recommendation letters (local log, not on GitHub):

```bash
.venv/bin/python trajectory/plot_trajectory.py --letters
```

Copy [`recommendation_letters.example.yaml`](recommendation_letters.example.yaml) to `trajectory/data/recommendation_letters.yaml` if needed. Prose index: [`LETTERS.md`](LETTERS.md) (gitignored). Tell your agent in chat to append records; each calendar year under a type counts as one letter.

**Plot groups:** career letters (grad / postdoc / faculty / industrial / promotion) each plot separately; fellowships & programs merged; national/international faculty award nominations merged (reserved, empty until added); immigration merged.

## Outputs (`trajectory/output/`, gitignored)

| File | Content |
|------|---------|
| `pubs_annual.png`, `pubs_cumulative.png` | Refereed / Editor / Contributor + Total |
| `talks_annual.png`, `talks_cumulative.png` | Talk categories + Total |
| `service_annual.png`, `service_cumulative.png` | Chair, Workshop organizer, Committee, Session convener + Total |
| `letters_annual.png` | Stacked bar by plot group (career types explicit) |
| `letters_cumulative.png` | Cumulative letter counts by type |
| `letters_detail.csv` | Flat log: year, type, name, note |
| `citations_by_pub_year.png` | inSPIRE snapshot summed by publication year |
| `citations_cumulative_stock.png` | Cumulative citation stock through each pub year |
| `summary_table.csv` | Year × all annual series |

## Milestones

Edit [`milestones.yaml`](milestones.yaml): grad school through **2015-08**, MS **2011-12**, postdocs (Fermilab → Maryland), UMN faculty bands, and personal markers (`kind: personal`). Dates use `YYYY-MM`; bands control background shading.

## Data sources

- `data/publications.yaml` — publication `year` and `section`
- `data/talks.yaml` — non-placeholder talks; includes scheduled/future
- `data/source/service.yaml` — workshop/program org + session convening

## Service parsing notes

- Snowmass convener (`2020---2022`) counts in **2020** only.
- Panelist entries are omitted from curves (noted in console).
- Optional overrides: `trajectory/data/service_overrides.yaml` (gitignored).

## Citations

- **Refereed papers only** (~80); editor/contributor white papers excluded.
- Uses today's inSPIRE `citation_count` — not citations received per calendar year.
- Cache: `trajectory/data/inspire_citations.yaml` (gitignored).

### Review / exclude papers

List all papers with citation counts:

```bash
.venv/bin/python trajectory/plot_trajectory.py --list-citations
```

Writes `trajectory/output/citations_inventory.csv` with columns: arxiv, year, citations, excluded, review_candidate, title.

To omit review articles or guides from plots, add arXiv IDs to [`citation_exclusions.yaml`](citation_exclusions.yaml):

```yaml
exclude_arxiv:
  - "2103.14043"   # Muon Smasher's Guide
```

Then regenerate citation figures:

```bash
.venv/bin/python trajectory/plot_trajectory.py --citations
```

Papers marked `review_candidate: true` in the CSV are heuristic flags (guide, review, report, etc.) — you confirm exclusions manually.
