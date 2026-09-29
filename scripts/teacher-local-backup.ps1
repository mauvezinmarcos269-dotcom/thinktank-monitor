param(
    [string]$OutputRoot = "local-backups",
    [switch]$SkipMinio
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $repoRoot $OutputRoot
$backupDir = Join-Path $backupRoot $timestamp
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

Write-Host "Creating ThinkTank Monitor backup..."
Write-Host "Backup directory: $backupDir"

$dbBackup = Join-Path $backupDir "postgres-thinktank-monitor.sql"
docker compose exec -T postgres pg_dump -U thinktank -d thinktank_monitor | Out-File -FilePath $dbBackup -Encoding utf8
Write-Host "Database backup written: $dbBackup"

$envBackupDir = Join-Path $backupDir "env"
New-Item -ItemType Directory -Force -Path $envBackupDir | Out-Null

if (Test-Path ".env") {
    Copy-Item -LiteralPath ".env" -Destination (Join-Path $envBackupDir "root.env")
    Write-Host "Root .env copied."
}

if (Test-Path "backend\.env") {
    Copy-Item -LiteralPath "backend\.env" -Destination (Join-Path $envBackupDir "backend.env")
    Write-Host "Backend .env copied."
}

if (-not $SkipMinio) {
    $minioContainer = docker compose ps -q minio
    if ($minioContainer) {
        $minioBackupDir = Join-Path $backupDir "minio-data"
        docker cp "${minioContainer}:/data" $minioBackupDir
        Write-Host "MinIO data copied: $minioBackupDir"
    } else {
        Write-Host "MinIO container not found; skipped MinIO backup."
    }
} else {
    Write-Host "MinIO backup skipped by request."
}

$manifestPath = Join-Path $backupDir "manifest.txt"
@(
    "ThinkTank Monitor local backup",
    "CreatedAt=$((Get-Date).ToString('s'))",
    "Repository=$repoRoot",
    "DatabaseBackup=$dbBackup",
    "MinioIncluded=$(-not $SkipMinio)"
) | Out-File -FilePath $manifestPath -Encoding utf8

Write-Host ""
Write-Host "Backup complete."
Write-Host "Keep this folder somewhere safe: $backupDir"
