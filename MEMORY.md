### Last Updated: 2026-07-23T14:38 | Active Environment: Mac
### Repo Visibility: Pre-public

### Current Project State
- **High-Level Objective:** Hugo personal website (Zhen Liu) — publications, talks, news, research group, GitHub Pages deploy.
- **Recent Progress:**
  - **CV refresh (2026-07-23):** Imported `Material/ZhenLiu_CV.tex` (from Downloads). Added Aspen Jul 2026 seminar; added JCAP to referee list; kept full *New Gauge Forces…* title; removed duplicate ZPrime seminar; publication tags restored after import.
  - **Research group** (`/mentoring/`): two-column layout; UMN PhD vs visiting grads; visiting periods fixed.
  - **Homepage:** 8 featured pubs; news reverse-chronological; trajectory milestones local-only.

### Technical Context & Constraints
- **CV import:** TeX-first — `Material/ZhenLiu_CV.tex` (gitignored) via `scripts/parse_cv_html.py` → `parse_cv_tex.py`. Do **not** use legacy HTML. Hand-edits in `data/source/cv_hand_edits.yaml` (Aspen talk fields; New Gauge Forces title; mentoring visiting/UMN periods).
- **Mentoring:** `data/source/mentoring.yaml`; visiting flag via hand-edits; layout `layouts/mentoring/single.html`.
- **Trajectory:** `trajectory/milestones.yaml` (`YYYY-MM`); outputs in `trajectory/output/` local-only.
- **Unresolved Issues / Roadblocks:** 1 publication may still use provisional tags (`approve_publication_tags.py --list`). Reorganize long-term visitors into a separate tile when more arrive. CV import currently drops `tags` — re-run tag restore/sync after each parse.

### Next Action Items
1. [ ] **Immediate Next Step:** Await user edits.
2. [ ] **Short-Term Tasks:** Confirm provisional publication tags if desired.
3. [ ] **Long-Term Backlog:** Split Visiting graduate students into own tile if roster grows; harden CV import to preserve publication tags.
