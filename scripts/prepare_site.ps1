# Mirror GitHub Actions prep so local builds match production (Windows).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (Test-Path ".\.venv\Scripts\python.exe") {
    $Py = ".\.venv\Scripts\python.exe"
    & $Py -m pip install -q -r requirements.txt
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Py = "python"
    & $Py -m pip install -q -r requirements.txt
} else {
    Write-Error "python or .venv required"
}

& $Py scripts/sync_material_media.py
& $Py scripts/sync_featured_publications.py
& $Py scripts/sync_publication_tags.py
& $Py scripts/clean_bibliography_data.py
& $Py scripts/sync_random_gallery_from_folders.py

Write-Host "Site prep complete (media, featured pubs, bibliography cleanup)."
