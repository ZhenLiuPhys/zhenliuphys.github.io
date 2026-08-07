### Last Updated: 2026-08-07T01:30 | Active Environment: Windows
### Repo Visibility: Pre-public

### Current Project State
- **High-Level Objective:** Hugo personal website (Zhen Liu) — publications, talks, news, research group, GitHub Pages deploy.
- **Recent Progress:**
  - `.gitignore` now excludes personal `Aspen/` and `Activities/` archives (not for public site).
  - Prior: CV refresh, trajectory canvas (machine-local), mentoring layout on `main`.

### Technical Context & Constraints
- **CV import:** TeX-first via gitignored `Material/ZhenLiu_CV.tex`; hand-edits in `data/source/cv_hand_edits.yaml`.
- **Trajectory:** outputs gitignored; canvas `research-trajectory.canvas.tsx` is machine-local.
- **Windows note:** `scripts/prepare_site.sh` may show mode-only dirty (755↔644); do not commit that flip.

### Next Action Items
1. [ ] **Immediate:** Await content edits.
2. [ ] **Short-Term:** Confirm provisional publication tags if desired.
3. [ ] **Long-Term:** Preserve tags on CV import; visiting-grad tile if roster grows.
