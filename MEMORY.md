### Last Updated: 2026-07-27T10:52 | Active Environment: Mac
### Repo Visibility: Pre-public

### Current Project State
- **High-Level Objective:** Hugo personal website (Zhen Liu) — publications, talks, news, research group, GitHub Pages deploy.
- **Recent Progress:**
  - **CV refresh (2026-07-23):** Imported TeX CV; Aspen Jul 2026 seminar; JCAP referee; full *New Gauge Forces…* title kept; ZPrime seminar duplicate removed; tags restored; committed/pushed `947a03f`.
  - **Trajectory self-monitor (2026-07-27):** Regenerated local `trajectory/output/` from current YAML. Cursor canvas `research-trajectory.canvas.tsx` (IDE canvases folder, outside this repo) embeds annual/cumulative pubs/talks/service/letters/citations for private monitoring. Not website content; PNGs/CSVs remain gitignored.
  - Mentoring layout, homepage 8 pubs, news sort — already on `main`.

### Technical Context & Constraints
- **CV import:** TeX-first — `Material/ZhenLiu_CV.tex` (gitignored) via `scripts/parse_cv_html.py` → `parse_cv_tex.py`. Hand-edits: `data/source/cv_hand_edits.yaml`. Import drops `tags` — re-run `sync_publication_tags.py` / restore after each parse.
- **Trajectory:** `trajectory/milestones.yaml` + `plot_trajectory.py`; outputs in `trajectory/output/` (gitignored). Self-monitor canvas lives under Cursor `canvases/research-trajectory.canvas.tsx` (machine-local, not website).
- **Mentoring:** `data/source/mentoring.yaml`; visiting via hand-edits.
- **Unresolved Issues / Roadblocks:** 1 publication may still use provisional tags (`approve_publication_tags.py --list`). Harden CV import to preserve publication tags. Split Visiting grads into own tile if roster grows.

### Next Action Items
1. [ ] **Immediate Next Step:** Await user edits.
2. [ ] **Short-Term Tasks:** Confirm provisional publication tags if desired; refresh trajectory canvas after next CV/YAML change.
3. [ ] **Long-Term Backlog:** Preserve tags on CV import; visiting-grad tile if needed.
