#!/usr/bin/env bash
# Mirror GitHub Actions prep so local builds match production.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
elif [[ -x .venv/Scripts/python.exe ]]; then
  PY=.venv/Scripts/python.exe
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "error: python3 or .venv required" >&2
  exit 1
fi

if [[ -x .venv/bin/pip ]]; then
  .venv/bin/pip install -q -r requirements.txt
elif [[ -x .venv/Scripts/python.exe ]]; then
  .venv/Scripts/python.exe -m pip install -q -r requirements.txt
else
  pip install -q -r requirements.txt
fi
"$PY" scripts/sync_material_media.py
"$PY" scripts/sync_featured_publications.py
"$PY" scripts/clean_bibliography_data.py
"$PY" scripts/sync_random_gallery_from_folders.py

echo "Site prep complete (Material images, gallery YAML, featured pubs, bibliography cleanup)."
