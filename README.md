# Zhen Liu Academic Website (Hugo + GitHub Pages)

**Live site:** https://zhenliu.net/

Hugo static site deployed to GitHub Pages. YAML data drives publications, talks, and profile content; layouts render HTML.

| If you want to… | Go to |
|-----------------|--------|
| Preview or build locally | [Local build](#local-build) |
| Refresh publications & talks from CV | [CV update](#cv-update-local-only) |
| Edit profile, news, highlights | [What to edit](#what-to-edit) |
| Pre-launch / QA | [docs/launch-checklist.md](docs/launch-checklist.md) |

---

## Project structure

```
PersonalWebsite/
├── hugo.toml              Site config (baseURL, params)
├── data/                  YAML content (publications, talks, news, source/*)
├── content/               Page intros (Markdown)
├── layouts/               HTML templates
├── assets/css/            Styles
├── static/                Images, CNAME, JS (copied to site root)
├── Material/              Local portrait + research banner (CV TeX gitignored)
├── scripts/               prepare_site, CV parser, link check
├── docs/launch-checklist.md   QA and DNS checklist
└── .github/workflows/deploy.yml   CI: prepare → hugo → Pages
```

**Do not commit:** `public/`, `.venv/`, `backups/`, CV TeX/PDF/HTML (see `.gitignore`).

---

## Local build

**Requirements:** [Hugo extended](https://gohugo.io/installation/) 0.162.0, Python 3 + `pip install -r requirements.txt`, `Material/profilephoto.jpg` and `Material/researchsummary.jpg`.

```bash
./scripts/prepare_site.sh
hugo server -D                    # http://localhost:1313
```

**Production check (matches CI):**

```bash
./scripts/prepare_site.sh
hugo --minify --cleanDestinationDir
python3 scripts/check_internal_links.py
```

---

## CV update (local only)

CV source files stay on your machine (`Material/ZhenLiu_CV.tex` is gitignored). Run the parser locally, commit updated YAML, then push.

```bash
.venv/bin/python scripts/parse_cv_html.py
.venv/bin/python scripts/sync_publication_tags.py
.venv/bin/python scripts/clean_bibliography_data.py
./scripts/prepare_site.sh
hugo --minify
.venv/bin/python scripts/check_internal_links.py
```

Publication topic tags live in `data/source/publication_tags.yaml` (your **confirmed** standard). Validate with `python scripts/validate_publication_tags.py`.

**Tag workflow**

| Step | What happens |
|------|----------------|
| Confirmed tags | `data/source/publication_tags.yaml` — your approved tags; never auto-overwritten |
| New CV papers | `sync_publication_tags.py` auto-drafts tags to `backups/publication-tag-proposals.yaml` (local, gitignored) |
| Site build | Uses confirmed tags; falls back to provisional drafts for new papers until you confirm |
| Your review | `python scripts/approve_publication_tags.py --list` |
| Confirm | Edit `backups/publication-tag-approvals.json` (from `--write-template`), then `--approvals`; or edit `publication_tags.yaml` directly |
| Bulk reset | `python scripts/generate_publication_tags.py --force` only if you intentionally replace all confirmed tags |

Heuristic suggestions that differ from your confirmed tags are written to `backups/publication-tag-review.yaml` for optional review (informational only).

If the parser reports conflicts with hand-edited YAML, review `backups/cv-conflict-approvals.json` (local, gitignored) and rerun with `--conflict-approvals` or `--approve-conflicts` after confirmation.

**Usually auto-updated:** `data/publications.yaml`, `data/talks.yaml`, `data/source/service.yaml`, `data/source/teaching.yaml`, `data/source/mentoring.yaml`, `data/photos.yaml`.

**Hand-edit separately:** `data/source/selected_publications.yaml`, `selected_talks.yaml`, `news.yaml`, `profile.yaml`, `research_themes.yaml`, `mentoring.yaml`.

---

## What to edit

| Goal | File(s) |
|------|---------|
| Name, email, links | `data/source/profile.yaml` |
| Homepage publication cards | `data/source/selected_publications.yaml` |
| Publication topic filters | `data/source/publication_tags.yaml` (confirmed); provisional drafts in `backups/` |
| Selected talks | `data/source/selected_talks.yaml` |
| News feed | `data/news.yaml` |
| Research themes | `data/source/research_themes.yaml` |
| Group members | `data/source/mentoring.yaml` |
| Page titles / blurbs | `content/*.md` |
| Look & layout | `layouts/`, `assets/css/main.css` |

---

## Deploy

Push to **`main`** → GitHub Actions runs `prepare_site.sh`, `hugo --minify`, link check, then publishes to Pages.

Custom domain: `static/CNAME` → `zhenliu.net`. DNS and HTTPS steps: **[docs/launch-checklist.md](docs/launch-checklist.md)**.

```bash
git add -A && git status
git commit -m "Describe your change"
git push origin main
```

---

## Live pages

| URL | Primary data |
|-----|----------------|
| `/` | `data/source/*`, `data/news.yaml` |
| `/publications/` | `data/publications.yaml` |
| `/talks/` | `data/talks.yaml`, `data/source/selected_talks.yaml` |
| `/news/` | `data/news.yaml`, `data/source/media.yaml` |
| `/mentoring/` | `data/source/mentoring.yaml` |
| `/service/` | `data/source/service.yaml` |
| `/teaching/` | `data/source/teaching.yaml`, `data/talks.yaml` |
| `/contact/` | `data/source/profile.yaml` |
| `/cv/` | Highlights only (no public PDF) |
