### Last Updated: 2026-07-10T20:25 | Active Environment: Mac
### Repo Visibility: Pre-public

### Current Project State
- **High-Level Objective:** Hugo personal website (Zhen Liu) — publications, talks, news, research group, GitHub Pages deploy.
- **Recent Progress:**
  - **Research group** (`/mentoring/`): two-column layout (grads+postdocs left; research grads/undergrads right); Graduate Students split into **UMN PhD students** vs **Visiting graduate students** (`visiting: true` on Yuxin Liu); section notes for research tiers; corrected visiting periods (Nick, Yiheng, Jett).
  - **Homepage:** selected publications showcase shows **8** items (`featured-pubs-showcase.js`).
  - **News:** reverse-chronological sort via `news-sorted.html`; dates normalized to `YYYY-MM`.
  - **Trajectory (local):** month-precise career bands (no overlap), academic + personal markers in `trajectory/milestones.yaml`; plots regenerated under `trajectory/output/` (gitignored).
  - Site content commits on `main` already pushed; wrap-up includes remaining trajectory milestone code.

### Technical Context & Constraints
- **Mentoring:** `data/source/mentoring.yaml`; visiting flag preserved via `cv_hand_edits.yaml`; layout `layouts/mentoring/single.html` + `mentoring-core-row.html`.
- **Trajectory:** `trajectory/milestones.yaml` uses `YYYY-MM`; bands abut at next `start`; personal points use `kind: personal`. Outputs in `trajectory/output/` are local-only.
- **Unresolved Issues / Roadblocks:** 1 publication may still use provisional tags (`approve_publication_tags.py --list`). Reorganize long-term visitors into a separate tile when more arrive.

### Next Action Items
1. [ ] **Immediate Next Step:** Await user edits.
2. [ ] **Short-Term Tasks:** Confirm provisional publication tags if desired; push wrap-up commit when ready.
3. [ ] **Long-Term Backlog:** CV refresh via `scripts/parse_cv_html.py`; split Visiting graduate students into own tile if roster grows.
