# Creates a "Trozovka Notes" shortcut on the Desktop so you can launch the
# app on demand by double-clicking it. Does NOT add anything to Windows
# Startup — auto-launching at login is what tripped Bitdefender's behavior
# blocker (silently registering a background process at boot looks like
# persistence malware), which killed the app and everything alongside it,
# including WSL.
#
# Run once from Windows PowerShell: .\create-desktop-shortcut.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainScript = Join-Path $repoRoot "main.py"
$pythonw = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\pythonw.exe"

if (-not (Test-Path $pythonw)) {
    throw "pythonw.exe not found at $pythonw - edit this script if your Python install path differs."
}

$desktopDir = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopDir "Trozovka Notes.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$mainScript`""
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "Trozovka Notes - desktop sticky notes"
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath"
Write-Host "Double-click it any time to launch Trozovka Notes."
