# Removes the Desktop shortcut installed by create-desktop-shortcut.ps1.
# Run from Windows PowerShell: .\remove-desktop-shortcut.ps1

$desktopDir = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopDir "Trozovka Notes.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath
    Write-Host "Removed: $shortcutPath"
} else {
    Write-Host "No desktop shortcut found at $shortcutPath"
}
