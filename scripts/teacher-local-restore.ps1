param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [switch]$SkipCurrentBackup,
    [switch]$SkipMinio,
    [switch]$RestoreEnv
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$resolvedBackupDir = Resolve-Path -LiteralPath $BackupDir -ErrorAction Stop
$backupPath = $resolvedBackupDir.Path
$dbBackup = Join-Path $backupPath "postgres-thinktank-monitor.sql"
$minioBackup = Join-Path $backupPath "minio-data"
$rootEnvBackup = Join-Path $backupPath "env\root.env"
$backendEnvBackup = Join-Path $backupPath "env\backend.env"

if (-not (Test-Path -LiteralPath $dbBackup)) {
    throw "Database backup not found: $dbBackup"
}

Write-Host "ThinkTank Monitor restore"
Write-Host "Backup directory: $backupPath"
Write-Host ""
Write-Host "This operation will overwrite the local database."
if ((Test-Path -LiteralPath $minioBackup) -and (-not $SkipMinio)) {
    Write-Host "This operation will also replace MinIO data."
}
if ($RestoreEnv) {
    Write-Host "This operation will restore .env files from the backup."
}
Write-Host ""

$confirmation = Read-Host "Type RESTORE to continue"
if ($confirmation -ne "RESTORE") {
    Write-Host "Restore cancelled."
    exit 0
}

if (-not $SkipCurrentBackup) {
    Write-Host ""
    Write-Host "Creating safety backup before restore..."
    & (Join-Path $PSScriptRoot "teacher-local-backup.ps1")
}

Write-Host ""
Write-Host "Ensuring services are running..."
& (Join-Path $PSScriptRoot "teacher-local-start.ps1")

Write-Host ""
Write-Host "Restoring PostgreSQL database..."
docker compose exec -T postgres psql -U thinktank -d thinktank_monitor -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO thinktank; GRANT ALL ON SCHEMA public TO public;"
Get-Content -LiteralPath $dbBackup -Raw | docker compose exec -T postgres psql -U thinktank -d thinktank_monitor -v ON_ERROR_STOP=1

if ((Test-Path -LiteralPath $minioBackup) -and (-not $SkipMinio)) {
    Write-Host ""
    Write-Host "Restoring MinIO data..."
    $minioContainer = docker compose ps -q minio
    if (-not $minioContainer) {
        throw "MinIO container not found."
    }

    docker compose exec -T minio sh -c "rm -rf /data/*"
    docker cp "${minioBackup}/." "${minioContainer}:/data"
    docker compose restart minio
} elseif ($SkipMinio) {
    Write-Host "MinIO restore skipped by request."
} else {
    Write-Host "MinIO backup directory not found; skipped MinIO restore."
}

if ($RestoreEnv) {
    Write-Host ""
    Write-Host "Restoring environment files..."
    if (Test-Path -LiteralPath $rootEnvBackup) {
        Copy-Item -LiteralPath $rootEnvBackup -Destination ".env" -Force
        Write-Host "Restored root .env."
    }
    if (Test-Path -LiteralPath $backendEnvBackup) {
        Copy-Item -LiteralPath $backendEnvBackup -Destination "backend\.env" -Force
        Write-Host "Restored backend .env."
    }
}

Write-Host ""
Write-Host "Restarting services..."
docker compose restart

Write-Host ""
Write-Host "Running health check..."
& (Join-Path $PSScriptRoot "teacher-local-health.ps1")

Write-Host ""
Write-Host "Restore complete."
