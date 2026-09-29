$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "ThinkTank Monitor service status:"
docker compose ps

Write-Host ""
Write-Host "If frontend is running, open: http://localhost:3000"
