### Last Updated: 2026-09-24T09:11 | Active Environment: Mac
### Repo Visibility: Pre-public

### Current Project State
- **High-Level Objective:** Hugo personal website (Zhen Liu) — publications, talks, news, research group, GitHub Pages deploy.
- **Recent Progress:**
  - CV refresh from updated TeX: new paper `2608.02718`, journal updates (PRD/JHEP/CPC), talks (Queen’s, KPS scheduled, NEXUS/Dali/Fudan unscheduled), news items for Aug–Sep 2026.
  - Unified pub filter tags `qis` + `quantum-sensing` → `sensing-qis` (“(Quantum) Sensing & QIS”).
  - Pheno plenary heuristic fixed (only 2020/2026); MagLev Pheno-DPF 2024 no longer mislabeled plenary.
  - CI fix: `scripts/prepare_site.sh` LF + `.gitattributes` (`*.sh text eol=lf`) after CRLF broke Actions bash.
  - Parser hardening: author-aware titles, bare DOIs from `\href{10.…}`, submitted venue display, overview-talk venue stripping.

### Technical Context & Constraints
- **CV import:** TeX-first via gitignored `Material/ZhenLiu_CV.tex`; hand-edits in `data/source/cv_hand_edits.yaml`; conflict approvals in gitignored `backups/`.
- **Pub tags:** confirmed in `data/source/publication_tags.yaml`; vocab in `data/source/publication_tag_vocab.yaml`.
- **Shell scripts:** keep Unix LF (see `.gitattributes`); avoid committing CRLF from Drive/Windows sync.
- **Trajectory:** outputs gitignored; canvas is machine-local, not deployed.
- **Windows note:** `prepare_site.sh` mode-only dirty (755↔644) — do not commit that flip.

### Next Action Items
1. [ ] **Immediate:** Optional — apply humanizer rewrites to `profile.yaml` hero / research copy (drafted earlier, not applied).
2. [ ] **Short-Term:** Curate `selected_talks.yaml` / `selected_publications.yaml` if homepage highlights should include new CV items.
3. [ ] **Long-Term:** Visiting-grad tile if roster grows; keep watching CV re-parse for duplicate talk IDs when “(scheduled)” is dropped.
