@echo off
REM Site prep for Windows (no PowerShell execution policy required).
setlocal
cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

"%PY%" -m pip install -q -r requirements.txt
if errorlevel 1 exit /b 1

"%PY%" scripts\sync_material_media.py
if errorlevel 1 exit /b 1

"%PY%" scripts\sync_featured_publications.py
if errorlevel 1 exit /b 1

"%PY%" scripts\clean_bibliography_data.py
if errorlevel 1 exit /b 1

"%PY%" scripts\sync_random_gallery_from_folders.py
if errorlevel 1 exit /b 1

echo Site prep complete (media, featured pubs, bibliography cleanup).
