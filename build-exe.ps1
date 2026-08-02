# Builds a standalone Trozovka Notes.exe (no Python install required to run it).
# Run from Windows PowerShell, from the repo root: .\build-exe.ps1
# Output: dist\Trozovka Notes.exe

$ErrorActionPreference = "Stop"

python -m pip install --quiet pyinstaller
python -m PyInstaller --onefile --windowed --name "Trozovka Notes" main.py

Write-Host "Built: dist\Trozovka Notes.exe"
