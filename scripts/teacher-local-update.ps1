param(
    [switch]$SkipBackup,
    [switch]$SkipPull,
    [switch]$SkipMigrate,
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "teacher-local-docker.ps1")

function Assert-LastCommandSucceeded {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

Write-Host "Updating ThinkTank Monitor local deployment..."
Write-Host "Repository: $repoRoot"
Assert-TeacherLocalDockerReady

if (-not $SkipBackup) {
    Write-Host "Step 1/8: backup current data"
    & (Join-Path $PSScriptRoot "teacher-local-backup.ps1")
    Assert-LastCommandSucceeded "Backup"
} else {
    Write-Host "Step 1/8: backup skipped"
}

Write-Host "Step 2/8: stop scheduled and API producers"
docker compose stop celery-beat backend
Assert-LastCommandSucceeded "Stop producers"

Write-Host "Step 3/8: let the old worker finish active tasks"
docker compose stop --timeout 900 celery-worker
Assert-LastCommandSucceeded "Stop worker"

$queuedTasks = docker compose exec -T redis redis-cli LLEN celery
Assert-LastCommandSucceeded "Inspect pending queue"
$unackedTasks = docker compose exec -T redis redis-cli HLEN unacked
Assert-LastCommandSucceeded "Inspect unacknowledged tasks"
if ([int]$queuedTasks -ne 0 -or [int]$unackedTasks -ne 0) {
    throw "Pending Celery tasks remain (queued=$queuedTasks, unacked=$unackedTasks). Review them before continuing; no tasks were deleted."
}

if (-not $SkipPull) {
    Write-Host "Step 4/8: pull latest code"
    git pull --ff-only
    Assert-LastCommandSucceeded "Git pull"
} else {
    Write-Host "Step 4/8: git pull skipped"
}

Write-Host "Step 5/8: build images without starting application processes"
docker compose build backend celery-worker celery-beat frontend
Assert-LastCommandSucceeded "Build images"

if (-not $SkipMigrate) {
    Write-Host "Step 6/8: run database migrations in a one-off backend"
    docker compose run --rm --no-deps backend alembic upgrade head
    Assert-LastCommandSucceeded "Database migration"
} else {
    Write-Host "Step 6/8: database migration skipped"
}

docker compose run --rm --no-deps backend alembic current --check-heads
Assert-LastCommandSucceeded "Database revision check"

Write-Host "Step 7/8: verify outbound is disabled, then start the new processes"
docker compose run --rm --no-deps backend python -c "from app.core.config import settings; assert not settings.LLM_OUTBOUND_ENABLED, 'LLM_OUTBOUND_ENABLED must be false during this rollout'"
Assert-LastCommandSucceeded "Outbound gate"
docker compose up -d --no-build backend celery-worker celery-beat frontend
Assert-LastCommandSucceeded "Start new processes"

if (-not $SkipHealthCheck) {
    Write-Host "Step 8/8: run health check"
    & (Join-Path $PSScriptRoot "teacher-local-health.ps1")
    Assert-LastCommandSucceeded "Health check"
} else {
    Write-Host "Step 8/8: health check skipped"
}

Write-Host "Update finished."
Write-Host "Open http://localhost:3000 after all services are healthy."
