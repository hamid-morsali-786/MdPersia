$ErrorActionPreference = "Stop"

$source = Join-Path $env:LOCALAPPDATA "ms-playwright"
$destination = Join-Path (Get-Location) "browsers"

if (-not (Test-Path $source)) {
    throw "Playwright browser cache was not found: $source"
}

New-Item -ItemType Directory -Force $destination | Out-Null
Copy-Item "$source\*" $destination -Recurse -Force

Write-Host "Copied Playwright browsers:"
Write-Host "  from: $source"
Write-Host "  to:   $destination"
Write-Host ""
Write-Host "Now test with:"
Write-Host "  fa-md-pdf .\docs --verbose"
