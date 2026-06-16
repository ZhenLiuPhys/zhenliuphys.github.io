# Launch checklist

> **Navigation:** [../README.md](../README.md) — project map and deploy steps.

Production: **`https://zhenliu.net/`** (GitHub Pages).

## 1. Local prep and build

```bash
chmod +x scripts/prepare_site.sh
./scripts/prepare_site.sh
hugo --minify --cleanDestinationDir
python3 scripts/check_internal_links.py
```

Expected:
- build succeeds,
- `check_internal_links.py` reports 0 broken links,
- no `public/files/zhen_liu_CV.pdf` artifact.

## 2. Spot-check in browser (local)

```bash
./scripts/prepare_site.sh && hugo server -D
```

Open `http://localhost:1313` and verify:

| Page | What to check |
|------|----------------|
| `/` | Hero intro text, research themes, featured highlights, Recent updates, Recent talks, photos-only gallery |
| `/publications/` | Selected block + search/filter behavior on full list |
| `/talks/` | Selected talks, List / By year toggle, full-list filters |
| `/news/` | Recent updates + archive + media coverage |
| `/mentoring/` | Research Group page title (**Group Members**) and four member tiles |
| `/service/` | Jump buttons, tile sections, PhD committee **counts** (UMN + external; no student names) |
| `/teaching/` | UMN course rows + Summer/Winter lecture block |
| `/contact/` | Email/address/profiles render correctly |
| `/cv/` | Highlights page only (no public PDF link) |
| `/research/` | Redirects to `/` |

Mobile: hamburger nav works and labels are current (including **Research Group**).

## 3. Git hygiene

- `.gitignore` includes `/public/`, `/resources/`, virtualenv files, local-only CV assets (`Material/ZhenLiu_CV.tex`, PDF, legacy HTML), and **`backups/`** (local-only; never commit).
- CV TeX/PDF stay local; confirm they are not tracked (`git ls-files Material/ZhenLiu_CV.tex` should be empty).

## 4. Push and GitHub Pages

1. Push to **`main`** on GitHub.
2. Pages source = **GitHub Actions** workflow.
3. CI builds with [`hugo.toml`](../hugo.toml) only (`baseURL = https://zhenliu.net/`).

## 5. Go live — DNS and custom domain

**GitHub:** **Settings → Pages** → Custom domain `zhenliu.net` → Save → **Enforce HTTPS** after DNS validates.

**Aliyun → 域名 → 解析** (nameservers stay HiChina; do not change NS records):

Remove old Google Sites records if present (CNAME `www` → `ghs.googlehosted.com`, TXT verification, old hosting A/CNAME). Keep MX and email TXT if you receive mail at `@zhenliu.net`.

**Four A records** on apex (`@`):

| Type | Host | Value |
|------|------|--------|
| A | @ | `185.199.108.153` |
| A | @ | `185.199.109.153` |
| A | @ | `185.199.110.153` |
| A | @ | `185.199.111.153` |

**Optional `www`:** CNAME `www` → `zhenliuphys.github.io`.

Checklist:

- [ ] GitHub **Settings → Pages** → Custom domain `zhenliu.net`
- [ ] Aliyun **A records** on `@` → four GitHub Pages IPs
- [ ] Remove old Google Sites CNAME / TXT records
- [ ] GitHub shows **DNS check successful**
- [ ] **Enforce HTTPS** enabled
- [ ] `https://zhenliu.net/` loads styled site (hard refresh)
- [ ] Nav links stay on `zhenliu.net`
- [ ] GA4 Realtime shows visit (`G-H476ZMS7TD`)
- [ ] Cancel old Aliyun web hosting; keep domain renewal

## Quick command summary

```bash
# Production build (matches CI)
./scripts/prepare_site.sh && hugo --minify --cleanDestinationDir && python3 scripts/check_internal_links.py
```
