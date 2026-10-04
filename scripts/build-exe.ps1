# Build standalone exe files for fa-md-pdf (CLI + GUI)
# Run from project root: .\scripts\build-exe.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Building fa-md-pdf executables ===" -ForegroundColor Cyan

# Ensure we're in project root
if (-not (Test-Path ".\pyproject.toml")) {
    Write-Host "Error: Run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Check PyInstaller
if (-not (& .\.venv\Scripts\pip.exe show pyinstaller 2>$null)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    & .\.venv\Scripts\pip.exe install pyinstaller -q
}

# Build CLI exe
Write-Host "`n--- Building fa-md-pdf.exe (CLI) ---" -ForegroundColor Green
$prevEA = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& .\.venv\Scripts\pyinstaller.exe fa-md-pdf.spec --noconfirm
Write-Host "`n--- Building fa-md-pdf-gui.exe (GUI) ---" -ForegroundColor Green
& .\.venv\Scripts\pyinstaller.exe fa-md-pdf-gui.spec --noconfirm
$ErrorActionPreference = $prevEA

# Show results
Write-Host "`n=== Build Results ===" -ForegroundColor Cyan
Get-ChildItem .\dist\*.exe | ForEach-Object {
    $sizeMB = [math]::Round($_.Length / 1MB, 1)
    Write-Host "  $($_.Name) - ${sizeMB} MB" -ForegroundColor White
}

Write-Host "`nFiles are in: .\dist\" -ForegroundColor Green
Write-Host @"

Usage:
  .\dist\fa-md-pdf.exe .\docs              # CLI conversion
  .\dist\fa-md-pdf.exe --gui               # Open GUI from CLI
  .\dist\fa-md-pdf-gui.exe                 # Open GUI directly

Note: Place browsers/, fonts/, and vendor/ next to the exe for offline operation.
"@ -ForegroundColor Gray
