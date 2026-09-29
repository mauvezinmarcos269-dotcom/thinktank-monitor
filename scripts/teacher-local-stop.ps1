$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Stopping ThinkTank Monitor local services..."
docker compose down

Write-Host ""
Write-Host "Services stopped. Data volumes are preserved."
