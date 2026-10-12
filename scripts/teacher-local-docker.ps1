function Invoke-TeacherLocalDocker {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCommand) {
        return [pscustomobject]@{
            Ok = $false
            ExitCode = 127
            Output = @("Docker CLI not found in PATH.")
            Text = "Docker CLI not found in PATH."
        }
    }

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & docker @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) {
            $exitCode = 0
        }
    } catch {
        $output = @($_.Exception.Message)
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $lines = @($output | ForEach-Object { $_.ToString() })
    $text = ($lines -join "`n").Trim()

    return [pscustomobject]@{
        Ok = ($exitCode -eq 0)
        ExitCode = $exitCode
        Output = $lines
        Text = $text
    }
}

function Get-TeacherLocalDockerFailureHint {
    param([object]$Result)

    $text = ""
    if ($Result -and $Result.Text) {
        $text = $Result.Text
    }

    if ($text -match "(?i)(not found in PATH|not recognized|CommandNotFoundException|term 'docker' is not recognized)") {
        return "Docker CLI was not found. Install Docker Desktop, then open a new PowerShell window."
    }

    if ($text -match "(?i)(permission denied|access is denied|unauthorized|denied.*dockerDesktop|dockerDesktop.*denied)") {
        return "Docker Desktop is installed, but this Windows user cannot access the Docker pipe."
    }

    if ($text -match "(?i)(cannot connect to the Docker daemon|daemon is not running|error during connect|dockerDesktopLinuxEngine|pipe.*cannot find|system cannot find the file)") {
        return "Docker Desktop is not reachable. Start Docker Desktop and wait until it is running."
    }

    if ([string]::IsNullOrWhiteSpace($text)) {
        return "Docker returned a non-zero exit code without details. Open Docker Desktop and retry."
    }

    return "Docker returned an error. Check Docker Desktop and retry."
}

function Write-TeacherLocalDockerActionLines {
    param([object]$Result)

    $text = ""
    if ($Result -and $Result.Text) {
        $text = $Result.Text
    }

    if ($text -match "(?i)(not found in PATH|not recognized|CommandNotFoundException|term 'docker' is not recognized)") {
        Write-Host "1. Install Docker Desktop."
        Write-Host "2. Close this PowerShell window and open a new one."
        Write-Host "3. Return to the project folder and rerun the health check."
        return
    }

    if ($text -match "(?i)(permission denied|access is denied|unauthorized|denied.*dockerDesktop|dockerDesktop.*denied)") {
        Write-Host "1. Open Docker Desktop with the current Windows user and wait until it is fully running."
        Write-Host "2. Close this PowerShell window, open a new PowerShell window, and retry."
        Write-Host "3. If it still fails, ask a maintainer to run this in an elevated PowerShell:"
        Write-Host '   net localgroup docker-users "$env:USERNAME" /add'
        Write-Host "4. Sign out of Windows and sign back in before rerunning this script."
        return
    }

    if ($text -match "(?i)(cannot connect to the Docker daemon|daemon is not running|error during connect|dockerDesktopLinuxEngine|pipe.*cannot find|system cannot find the file)") {
        Write-Host "1. Open Docker Desktop from the Start menu."
        Write-Host "2. Wait until Docker Desktop says the engine is running."
        Write-Host "3. Return to the project folder and rerun the health check."
        return
    }

    Write-Host "1. Open Docker Desktop and check for errors or pending updates."
    Write-Host "2. Open a new PowerShell window and rerun the health check."
    Write-Host "3. If it still fails, send the Docker output below to a maintainer."
}

function Get-TeacherLocalDockerShortOutput {
    param([object]$Result)

    if (-not $Result -or -not $Result.Output) {
        return ""
    }

    $allLines = @($Result.Output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $importantLines = @($allLines | Where-Object { $_ -match "(?i)(permission denied|access is denied|error|daemon|pipe|dockerDesktop|unauthorized)" })
    $lines = if ($importantLines.Count -gt 0) {
        @($importantLines | Select-Object -First 3)
    } else {
        @($allLines | Select-Object -First 3)
    }
    if ($lines.Count -eq 0) {
        return ""
    }

    $text = ($lines -join " | ")
    if ($text.Length -gt 88) {
        return "$($text.Substring(0, 88))..."
    }

    return $text
}

function Write-TeacherLocalDockerGuidance {
    param(
        [string]$Context = "Docker",
        [object]$Result
    )

    Write-Host "Suggested fix ($Context):" -ForegroundColor Yellow
    Write-TeacherLocalDockerActionLines -Result $Result

    $shortOutput = Get-TeacherLocalDockerShortOutput $Result
    if ($shortOutput) {
        Write-Host "Docker output summary: $shortOutput" -ForegroundColor DarkGray
    }

    Write-Host "After fixing Docker Desktop, rerun the command you just tried."
    Write-Host "To verify only, run: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\teacher-local-health.ps1"
}

function Test-TeacherLocalDockerReady {
    param([switch]$Quiet)

    $checks = @(
        [pscustomobject]@{ Context = "Docker command"; Arguments = @("--version") },
        [pscustomobject]@{ Context = "Docker Compose command"; Arguments = @("compose", "version") },
        [pscustomobject]@{ Context = "Docker daemon"; Arguments = @("info") }
    )

    foreach ($check in $checks) {
        $result = Invoke-TeacherLocalDocker -Arguments $check.Arguments
        if (-not $result.Ok) {
            if (-not $Quiet) {
                Write-TeacherLocalDockerGuidance -Context $check.Context -Result $result
            }
            return $false
        }
    }

    return $true
}

function Assert-TeacherLocalDockerReady {
    if (-not (Test-TeacherLocalDockerReady)) {
        Write-Host "Stopped because Docker Desktop is not ready for teacher local mode." -ForegroundColor Red
        exit 1
    }
}
