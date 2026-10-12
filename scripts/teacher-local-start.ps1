param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "teacher-local-docker.ps1")

Write-Host "Starting ThinkTank Monitor for local teacher use..."

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

function Get-ComposeServiceState {
    param([string]$Service)

    try {
        $containerResult = Invoke-TeacherLocalDocker -Arguments @("compose", "ps", "-q", $Service)
        if (-not $containerResult.Ok) {
            return "unknown"
        }

        $containerId = $containerResult.Text
        if (-not $containerId) {
            return "not-found"
        }

        $stateResult = Invoke-TeacherLocalDocker -Arguments @("inspect", "-f", "{{.State.Status}}", $containerId)
        if (-not $stateResult.Ok -or -not $stateResult.Text) {
            return "unknown"
        }

        return $stateResult.Text.Trim()
    } catch {
        return "unknown"
    }
}

function Format-PortListeners {
    param([object[]]$Listeners)

    if ($Listeners.Count -eq 0) {
        return "no listener"
    }

    return ($Listeners | ForEach-Object { "$($_.ProcessName)(pid=$($_.Pid))" }) -join ", "
}

function Test-RequiredPorts {
    $checks = @(
        [pscustomobject]@{ Name = "Frontend"; Port = 3000; Service = "frontend" },
        [pscustomobject]@{ Name = "Backend"; Port = 8000; Service = "backend" }
    )

    $blocked = $false

    Write-Host ""
    Write-Host "Checking required local ports..."

    foreach ($check in $checks) {
        $listeners = @(Get-PortListeners $check.Port)
        $serviceState = Get-ComposeServiceState $check.Service
        $detail = Format-PortListeners $listeners

        if ($listeners.Count -eq 0) {
            Write-Host "[OK] $($check.Name) port $($check.Port) is free."
            continue
        }

        if ($serviceState -eq "running") {
            Write-Host "[OK] $($check.Name) port $($check.Port) is already used by the Docker service ($detail)."
            continue
        }

        $blocked = $true
        Write-Host "[FAIL] $($check.Name) port $($check.Port) is already listening: $detail" -ForegroundColor Red
    }

    if (-not $blocked) {
        return
    }

    Write-Host ""
    Write-Host "The teacher Docker mode needs ports 3000 and 8000." -ForegroundColor Yellow
    Write-Host "If you want teacher mode, stop the process using those ports, or run powershell -NoProfile -ExecutionPolicy Bypass -File scripts\teacher-local-stop.ps1 if Docker services are stuck."
    Write-Host "If you want development mode, run scripts\start-local-backend.ps1 and scripts\start-local-frontend.ps1 instead."
    Write-Host "To keep Docker on 8000 and run isolated development, pass -Port 8001 to start-local-backend.ps1 and -BackendPort 8001 to start-local-frontend.ps1."
    throw "Required local ports are already occupied."
}

Assert-TeacherLocalDockerReady
Test-RequiredPorts

if ($Build) {
    docker compose up -d --build
} else {
    docker compose up -d
}
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose startup failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Startup command submitted."
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000"
Write-Host ""
Write-Host "Run powershell -NoProfile -ExecutionPolicy Bypass -File scripts\teacher-local-status.ps1 to check service status."
