$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "teacher-local-docker.ps1")

Write-Host "ThinkTank Monitor service status:"
Assert-TeacherLocalDockerReady
$status = Invoke-TeacherLocalDocker -Arguments @("compose", "ps")
if (-not $status.Ok) {
    Write-TeacherLocalDockerGuidance -Context "Docker Compose status" -Result $status
    exit 1
}
$status.Output | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "If frontend is running, open: http://localhost:3000"
