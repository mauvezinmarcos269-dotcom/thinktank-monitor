param(
    [string]$OutputRoot = "local-diagnostics",
    [int]$LogTail = 300
)

$ErrorActionPreference = "Continue"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "teacher-local-docker.ps1")

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$diagnosticRoot = Join-Path $repoRoot $OutputRoot
$diagnosticDir = Join-Path $diagnosticRoot $timestamp
New-Item -ItemType Directory -Force -Path $diagnosticDir | Out-Null

Write-Host "Collecting ThinkTank Monitor diagnostics..."
Write-Host "Output directory: $diagnosticDir"

function Save-CommandOutput {
    param(
        [string]$Path,
        [scriptblock]$Command
    )

    try {
        & $Command *> $Path
    } catch {
        "Command failed: $($_.Exception.Message)" | Out-File -FilePath $Path -Encoding utf8
    }
}

function Save-DockerOutput {
    param(
        [string]$Path,
        [string[]]$Arguments
    )

    Save-CommandOutput $Path {
        $result = Invoke-TeacherLocalDocker -Arguments $Arguments
        if ($result.Output -and $result.Output.Count -gt 0) {
            $result.Output
        }
        if (-not $result.Ok) {
            ""
            "Docker command failed: docker $($Arguments -join ' ')"
            "Diagnosis: $(Get-TeacherLocalDockerFailureHint $result)"
            Write-TeacherLocalDockerGuidance -Context "Docker diagnostics" -Result $result
        }
    }
}

Save-DockerOutput (Join-Path $diagnosticDir "docker-version.txt") @("--version")
Save-DockerOutput (Join-Path $diagnosticDir "docker-compose-version.txt") @("compose", "version")
Save-CommandOutput (Join-Path $diagnosticDir "docker-diagnosis.txt") {
    $ready = Test-TeacherLocalDockerReady
    "DockerReady=$ready"
}
Save-DockerOutput (Join-Path $diagnosticDir "docker-compose-ps.txt") @("compose", "ps")
Save-CommandOutput (Join-Path $diagnosticDir "git-version.txt") { git --version }
Save-CommandOutput (Join-Path $diagnosticDir "git-status.txt") { git status --short --branch }
Save-CommandOutput (Join-Path $diagnosticDir "git-log.txt") { git log -5 --oneline }

$services = @(
    "backend",
    "celery-worker",
    "celery-beat",
    "frontend",
    "postgres",
    "redis",
    "minio"
)

foreach ($service in $services) {
    $logPath = Join-Path $diagnosticDir "$service.log"
    Save-DockerOutput $logPath @("compose", "logs", "--tail", "$LogTail", $service)
}

$healthPath = Join-Path $diagnosticDir "health-check.txt"
Save-CommandOutput $healthPath { & (Join-Path $PSScriptRoot "teacher-local-health.ps1") }

$summaryPath = Join-Path $diagnosticDir "summary.txt"
@(
    "ThinkTank Monitor diagnostics",
    "CreatedAt=$((Get-Date).ToString('s'))",
    "Repository=$repoRoot",
    "LogTail=$LogTail",
    "Note=This package intentionally does not include .env files."
) | Out-File -FilePath $summaryPath -Encoding utf8

$zipPath = Join-Path $diagnosticRoot "thinktank-diagnostics-$timestamp.zip"
Compress-Archive -Path (Join-Path $diagnosticDir "*") -DestinationPath $zipPath -Force

Write-Host ""
Write-Host "Diagnostics complete."
Write-Host "Zip file: $zipPath"
Write-Host "This package does not include .env files."
