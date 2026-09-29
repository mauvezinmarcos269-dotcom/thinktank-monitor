param(
    [switch]$SkipBackup,
    [switch]$SkipPull,
    [switch]$SkipMigrate,
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Updating ThinkTank Monitor local deployment..."
Write-Host "Repository: $repoRoot"

if (-not $SkipBackup) {
    Write-Host ""
    Write-Host "Step 1/5: backup current data"
    & (Join-Path $PSScriptRoot "teacher-local-backup.ps1")
} else {
    Write-Host ""
    Write-Host "Step 1/5: backup skipped"
}

if (-not $SkipPull) {
    Write-Host ""
    Write-Host "Step 2/5: pull latest code"
    git pull --ff-only
} else {
    Write-Host ""
    Write-Host "Step 2/5: git pull skipped"
}

Write-Host ""
Write-Host "Step 3/5: rebuild and restart services"
& (Join-Path $PSScriptRoot "teacher-local-start.ps1") -Build

if (-not $SkipMigrate) {
    Write-Host ""
    Write-Host "Step 4/5: run database migrations"
    docker compose exec -T backend alembic upgrade head
} else {
    Write-Host ""
    Write-Host "Step 4/5: database migration skipped"
}

if (-not $SkipHealthCheck) {
    Write-Host ""
    Write-Host "Step 5/5: run health check"
    & (Join-Path $PSScriptRoot "teacher-local-health.ps1")
} else {
    Write-Host ""
    Write-Host "Step 5/5: health check skipped"
}

Write-Host ""
Write-Host "Update finished."
Write-Host "Open http://localhost:3000 after all services are healthy."
