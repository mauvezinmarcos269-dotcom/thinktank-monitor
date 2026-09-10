param(
    [int]$Port = 3001,
    [int]$BackendPort = 8001
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"

$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:$BackendPort"

Set-Location $frontendDir
npm run dev -- -p $Port
