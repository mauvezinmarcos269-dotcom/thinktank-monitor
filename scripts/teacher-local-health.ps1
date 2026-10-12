$ErrorActionPreference = "Continue"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "teacher-local-docker.ps1")

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

function Write-Skip {
    param(
        [string]$Name,
        [string]$Detail = ""
    )

    Write-Host "[SKIP] $Name $Detail" -ForegroundColor Yellow
}

function Wait-HttpEndpoint {
    param(
        [string]$Uri,
        [int]$Attempts = 15,
        [int]$DelaySeconds = 2
    )

    $lastError = "No response"
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                return [pscustomobject]@{
                    Ok = $true
                    Detail = "status=$($response.StatusCode), attempt=$attempt"
                }
            }
            $lastError = "status=$($response.StatusCode)"
        } catch {
            $lastError = $_.Exception.Message
        }

        if ($attempt -lt $Attempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    return [pscustomobject]@{
        Ok = $false
        Detail = $lastError
    }
}

function Get-PortListeners {
    param([int]$Port)

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        return @(
            foreach ($connection in $connections) {
                $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
                [pscustomobject]@{
                    Port = $Port
                    Pid = $connection.OwningProcess
                    ProcessName = if ($process) { $process.ProcessName } else { "unknown" }
                }
            }
        )
    } catch {
        $portPattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
        return @(
            netstat -ano | Where-Object { $_ -match $portPattern } | ForEach-Object {
                $pid = [int]$Matches[1]
                $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                [pscustomobject]@{
                    Port = $Port
                    Pid = $pid
                    ProcessName = if ($process) { $process.ProcessName } else { "unknown" }
                }
            }
        )
    }
}

function Format-PortListeners {
    param([object[]]$Listeners)

    if ($Listeners.Count -eq 0) {
        return "no listener"
    }

    return ($Listeners | ForEach-Object { "$($_.ProcessName)(pid=$($_.Pid))" }) -join ", "
}

Write-Host "ThinkTank Monitor local health check"
Write-Host "Repository: $repoRoot"
Write-Host ""

$dockerVersion = Invoke-TeacherLocalDocker -Arguments @("--version")
Write-Check "Docker command" $dockerVersion.Ok $dockerVersion.Text

$dockerComposeVersion = Invoke-TeacherLocalDocker -Arguments @("compose", "version")
Write-Check "Docker Compose command" $dockerComposeVersion.Ok $dockerComposeVersion.Text

$dockerInfo = Invoke-TeacherLocalDocker -Arguments @("info")
$dockerReady = ($dockerVersion.Ok -and $dockerComposeVersion.Ok -and $dockerInfo.Ok)
if ($dockerInfo.Ok) {
    Write-Check "Docker daemon" $true "ready"
} else {
    Write-Check "Docker daemon" $false (Get-TeacherLocalDockerFailureHint $dockerInfo)
    Write-TeacherLocalDockerGuidance -Context "Docker daemon" -Result $dockerInfo
}

Write-Host ""
Write-Host "Container status:"
if ($dockerReady) {
    $composeStatus = Invoke-TeacherLocalDocker -Arguments @("compose", "ps")
    if ($composeStatus.Ok) {
        $composeStatus.Output | ForEach-Object { Write-Host $_ }
    } else {
        Write-Check "Docker Compose status" $false (Get-TeacherLocalDockerFailureHint $composeStatus)
        Write-TeacherLocalDockerGuidance -Context "Docker Compose status" -Result $composeStatus
    }
} else {
    Write-Host "skipped because Docker Desktop is not ready"
}
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

if ($dockerReady) {
    foreach ($service in $expectedServices) {
        $containerResult = Invoke-TeacherLocalDocker -Arguments @("compose", "ps", "-q", $service)
        if (-not $containerResult.Ok -or -not $containerResult.Text) {
            Write-Check "Container $service" $false "not found"
            continue
        }

        $stateResult = Invoke-TeacherLocalDocker -Arguments @("inspect", "-f", "{{.State.Status}}", $containerResult.Text)
        $state = if ($stateResult.Ok) { $stateResult.Text } else { "unknown" }
        Write-Check "Container $service" ($state -eq "running") "state=$state"
    }
} else {
    foreach ($service in $expectedServices) {
        Write-Skip "Container $service" "Docker Desktop is not ready"
    }
}

Write-Host ""

if (-not $dockerReady) {
    Write-Host "Health check stopped early because Docker Desktop is not ready." -ForegroundColor Yellow
    Write-Host "Fix Docker Desktop first, then rerun: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\teacher-local-health.ps1"
    Write-Host ""
    Write-Host "Health check finished with failures." -ForegroundColor Red
    exit 1
}

$backendListeners = @(Get-PortListeners 8000)
Write-Check "Backend port 8000" ($backendListeners.Count -gt 0) (Format-PortListeners $backendListeners)

$backendHealth = Wait-HttpEndpoint "http://localhost:8000/health"
$backendHealthDetail = $backendHealth.Detail
if (-not $backendHealth.Ok -and $backendListeners.Count -eq 0) {
    $backendHealthDetail = "$backendHealthDetail; no listener on port 8000. Run powershell -NoProfile -ExecutionPolicy Bypass -File scripts\teacher-local-start.ps1 for teacher Docker mode."
}
Write-Check "Backend /health" $backendHealth.Ok $backendHealthDetail

$frontendListeners = @(Get-PortListeners 3000)
Write-Check "Frontend port 3000" ($frontendListeners.Count -gt 0) (Format-PortListeners $frontendListeners)

$frontendHealth = Wait-HttpEndpoint "http://localhost:3000"
$frontendHealthDetail = $frontendHealth.Detail
if (-not $frontendHealth.Ok -and $frontendListeners.Count -eq 0) {
    $frontendHealthDetail = "$frontendHealthDetail; no listener on port 3000. Run powershell -NoProfile -ExecutionPolicy Bypass -File scripts\teacher-local-start.ps1 for teacher Docker mode."
}
Write-Check "Frontend page" $frontendHealth.Ok $frontendHealthDetail

if ($dockerReady) {
    $celeryPing = Invoke-TeacherLocalDocker -Arguments @("compose", "exec", "-T", "celery-worker", "celery", "-A", "app.workers.celery_app.celery_app", "inspect", "ping")
    $celeryPingDetail = if ($celeryPing.Ok) { "ok" } else { Get-TeacherLocalDockerFailureHint $celeryPing }
    Write-Check "Celery worker ping" $celeryPing.Ok $celeryPingDetail
} else {
    Write-Skip "Celery worker ping" "Docker Desktop is not ready"
}

Write-Host ""
if ($hasFailure) {
    Write-Host "Health check finished with failures." -ForegroundColor Red
    exit 1
}

Write-Host "Health check passed." -ForegroundColor Green
