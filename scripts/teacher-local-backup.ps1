param(
    [string]$OutputRoot = "local-backups",
    [switch]$SkipMinio
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "teacher-local-docker.ps1")

Write-Host "Creating ThinkTank Monitor backup..."
Assert-TeacherLocalDockerReady

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $repoRoot $OutputRoot
$backupDir = Join-Path $backupRoot $timestamp
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Write-Host "Backup directory: $backupDir"

$dbBackup = Join-Path $backupDir "postgres-thinktank-monitor.sql"
docker compose exec -T postgres pg_dump -U thinktank -d thinktank_monitor | Out-File -FilePath $dbBackup -Encoding utf8
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $dbBackup) -or (Get-Item -LiteralPath $dbBackup).Length -eq 0) {
    throw "PostgreSQL backup failed or produced an empty file."
}
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
        if ($LASTEXITCODE -ne 0) {
            throw "MinIO backup failed."
        }
        Write-Host "MinIO data copied: $minioBackupDir"
    } else {
        throw "MinIO container not found. Use -SkipMinio only after explicitly deciding to omit its backup."
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
