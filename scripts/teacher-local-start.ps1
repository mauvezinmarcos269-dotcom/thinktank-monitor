param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Starting ThinkTank Monitor for local teacher use..."

if ($Build) {
    docker compose up -d --build
} else {
    docker compose up -d
}

Write-Host ""
Write-Host "Startup command submitted."
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000"
Write-Host ""
Write-Host "Run scripts\teacher-local-status.ps1 to check service status."
