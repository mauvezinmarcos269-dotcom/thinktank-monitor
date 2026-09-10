param(
    [int]$Port = 3001
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"

$netstat = netstat -ano
$portPattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+\d+\s*$"
$listeners = $netstat | Where-Object { $_ -match $portPattern }

if ($listeners.Count -gt 0) {
    Write-Error "Port $Port is listening. Stop the Next.js dev server before running a production build, otherwise frontend/.next may be corrupted."
}

Set-Location $frontendDir
npm run build
