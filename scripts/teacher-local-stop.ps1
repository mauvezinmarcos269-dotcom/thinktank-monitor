$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "teacher-local-docker.ps1")

Write-Host "Stopping ThinkTank Monitor local services..."
Assert-TeacherLocalDockerReady
docker compose down
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose stop failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Services stopped. Data volumes are preserved."
