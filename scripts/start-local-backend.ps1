param(
    [int]$Port = 8001,
    [string]$Queue = "thinktank-local-codex"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"

$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"
$env:CELERY_TASK_DEFAULT_QUEUE = $Queue

Set-Location $backendDir
poetry run uvicorn app.main:app --host 127.0.0.1 --port $Port --reload
