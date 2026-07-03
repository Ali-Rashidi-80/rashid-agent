# Rashid Agent — ARQ worker (local dev)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:PYTHONPATH = Join-Path $Root "backend"
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://127.0.0.1:6380/0" }

Set-Location (Join-Path $Root "backend")
Write-Host "Starting ARQ worker ..." -ForegroundColor Cyan
python -m arq worker.settings.WorkerSettings
