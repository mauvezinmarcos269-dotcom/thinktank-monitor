param(
    [string]$Queue = "thinktank-local-codex",
    [string]$LogLevel = "info"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"

$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"
$env:CELERY_TASK_DEFAULT_QUEUE = $Queue

Set-Location $backendDir
poetry run celery -A app.workers.celery_app.celery_app worker --pool=solo --concurrency=1 --loglevel=$LogLevel -Q $Queue -n "local-worker@%h"
