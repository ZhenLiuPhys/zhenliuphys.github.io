### Last Updated: 2026-06-19T14:00 | Active Environment: Mac
### Repo Visibility: Pre-public

### Current Project State
- **High-Level Objective:** Hugo personal website (Zhen Liu) — publications, talks, news, GitHub Pages deploy.
- **Recent Progress:**
  - **Talks page** (`layouts/talks/list.html`, `talk-line.html`, `talk-labels.html`, `assets/css/main.css`): full list in `section-block`; clickable year groups; multi-label badges (category + Scheduled + Selected) in fixed right aside; `(scheduled)` stripped from titles via `scripts/talk_fields.py`.
  - **Publications page** (`publication-line.html`, `assets/css/main.css`): topic keywords right-aligned on meta line.
  - **Publication tags** (`data/source/publication_tags.yaml`, `publication_tag_vocab.yaml`): renamed label **Dark Matter/Sector**; manual tag updates for arXiv 2109.01682, 2204.05296, 1709.06103, 1512.07624, 1312.4992, 2301.07117, 2104.00638, 2012.01443, 1210.7803; synced to `data/publications.yaml`.
  - **Gallery:** DPF-Pheno 2024 photo (`static/images/photos/pheno_umn_award.png`, `data/photos.yaml`).
  - Latest commit on `main`: talks labels + publication tags refresh (pushed).

### Technical Context & Constraints
- **Active Variables/Models:** Confirmed tags in `data/source/publication_tags.yaml`; vocab labels in `data/source/publication_tag_vocab.yaml`; after tag edits run `.venv/bin/python scripts/sync_publication_tags.py`.
- **Talk labels:** `layouts/partials/talk-labels.html` builds badge list; selected IDs from `data/source/selected_talks.yaml`.
- **Unresolved Issues / Roadblocks:** 1 publication still on provisional tags (see `approve_publication_tags.py --list`); `data/photos.yaml` has unstaged YAML wrap-only diff from gallery sync.

### Next Action Items
1. [ ] **Immediate Next Step:** Await user edits (publications, plots, talks, gallery).
2. [ ] **Short-Term Tasks:** Confirm provisional publication tag if desired; optionally discard or commit `photos.yaml` line-wrap.
3. [ ] **Long-Term Backlog:** Routine CV refresh via `scripts/parse_cv_html.py` when CV source updates.
