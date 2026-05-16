$ErrorActionPreference = "Stop"

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e .

New-Item -ItemType Directory -Force .\browsers | Out-Null

$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\browsers"
python -m playwright install chromium

Write-Host ""
Write-Host "Setup finished."
Write-Host "Offline browser path:"
Write-Host "  $PWD\browsers"
Write-Host ""
Write-Host "Make sure these files exist for fully offline Mermaid/Persian output:"
Write-Host "  .\vendor\mermaid.min.js"
Write-Host "  .\fonts\Vazirmatn-Regular.ttf"
Write-Host ""
Write-Host "Try:"
Write-Host "  fa-md-pdf .\examples\sample-fa.md --verbose"
