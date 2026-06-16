# Material folder (sync from your main machine)

> **Navigation:** [../README.md](../README.md) — full project map and CV import commands.

Files here are copied into `static/` by `scripts/sync_material_media.py` when you run site prep.

## Required for production-quality preview

| File | Destination | Typical size |
|------|-------------|--------------|
| `profilephoto.jpg` | `static/images/profile/profilephoto.jpg` | Usually 50 KB+ |
| `researchsummary.jpg` | `static/images/research/researchsummary.jpg` | Usually 100 KB+ |

**Copy both files from the computer where you maintain the site** if they are missing after cloud sync. Prep prints `MISSING` or `WARNING` if files are absent or look like placeholders.

After copying:

```bat
scripts\prepare_site.cmd
hugo server -D
```

Then hard-refresh the homepage and confirm your real portrait appears (not the gray SVG fallback).

## CV import (local only — not in public repo)

These paths are **gitignored**. Keep them on your machine for parser runs; only the generated YAML is committed to GitHub.

- `ZhenLiu_CV.tex` — primary input for `python scripts/parse_cv_html.py`
- `Zhen_Liu_CV.htm` or `Zhen_Liu_CV.html` — optional legacy input (used only with explicit `--input`)
- `Zhen_Liu_CV.pdf` (repo root) — optional local archive; not parsed, not deployed

Placeholder images may exist in this folder only for local builds until you replace them with your real assets.
