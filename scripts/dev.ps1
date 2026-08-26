# Rashid Agent — dev workflow (phase 0)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

& "$Root\scripts\infra-up.ps1"
if (-not $?) { exit 1 }
if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$Root\scripts\migrate.ps1"
if (-not $?) { exit 1 }
if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PYTHONPATH = Join-Path $Root "backend"
Set-Location (Join-Path $Root "backend")

# Background ARQ worker (KB ingest + telegram jobs)
& "$Root\scripts\smoke-worker.ps1" start
if (-not $?) { Write-Host "WARN: ARQ worker failed to start" -ForegroundColor Yellow }

Write-Host "Starting API on 127.0.0.1:8000 ..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
