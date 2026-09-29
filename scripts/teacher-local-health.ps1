$ErrorActionPreference = "Continue"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$hasFailure = $false

function Write-Check {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail = ""
    )

    if ($Ok) {
        Write-Host "[OK] $Name $Detail" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Name $Detail" -ForegroundColor Red
        $script:hasFailure = $true
    }
}

Write-Host "ThinkTank Monitor local health check"
Write-Host "Repository: $repoRoot"
Write-Host ""

$dockerVersion = docker --version 2>$null
Write-Check "Docker command" ($LASTEXITCODE -eq 0) $dockerVersion

docker compose version *> $null
Write-Check "Docker Compose command" ($LASTEXITCODE -eq 0)

Write-Host ""
Write-Host "Container status:"
docker compose ps
Write-Host ""

$expectedServices = @(
    "postgres",
    "redis",
    "minio",
    "backend",
    "celery-worker",
    "celery-beat",
    "frontend"
)

foreach ($service in $expectedServices) {
    $containerId = docker compose ps -q $service 2>$null
    if (-not $containerId) {
        Write-Check "Container $service" $false "not found"
        continue
    }

    $state = docker inspect -f "{{.State.Status}}" $containerId 2>$null
    Write-Check "Container $service" ($state -eq "running") "state=$state"
}

Write-Host ""

try {
    $backendHealth = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
    Write-Check "Backend /health" ($backendHealth.StatusCode -eq 200) "status=$($backendHealth.StatusCode)"
} catch {
    Write-Check "Backend /health" $false $_.Exception.Message
}

try {
    $frontendHealth = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 10
    Write-Check "Frontend page" ($frontendHealth.StatusCode -eq 200) "status=$($frontendHealth.StatusCode)"
} catch {
    Write-Check "Frontend page" $false $_.Exception.Message
}

docker compose exec -T celery-worker celery -A app.workers.celery_app.celery_app inspect ping *> $null
Write-Check "Celery worker ping" ($LASTEXITCODE -eq 0)

Write-Host ""
if ($hasFailure) {
    Write-Host "Health check finished with failures." -ForegroundColor Red
    exit 1
}

Write-Host "Health check passed." -ForegroundColor Green
