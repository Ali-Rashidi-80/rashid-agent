# Smoke test - requires infra (docker compose)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:PYTHONPATH = Join-Path $Root "backend"
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://127.0.0.1:6380/0" }
$env:ARQ_REDIS_URL = if ($env:ARQ_REDIS_URL) { $env:ARQ_REDIS_URL } else { "redis://127.0.0.1:6380/1" }

function Assert-StepSuccess {
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "== Rashid smoke: frontend lib ==" -ForegroundColor Cyan
& "$Root\scripts\verify-frontend-lib.ps1"
Assert-StepSuccess

Write-Host "== Rashid smoke: migrate database ==" -ForegroundColor Cyan
& "$Root\scripts\migrate.ps1"
Assert-StepSuccess

Write-Host "== Rashid smoke: ruff ==" -ForegroundColor Cyan
Set-Location $Root
python -m ruff check backend
Assert-StepSuccess

Write-Host "== Rashid smoke: ARQ worker for pytest ==" -ForegroundColor Cyan
& "$Root\scripts\smoke-worker.ps1" -Action start
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

try {
    Write-Host "== Rashid smoke: unit + integration (pytest) ==" -ForegroundColor Cyan
    python -m pytest backend/tests -q
    Assert-StepSuccess

    Write-Host "== Rashid smoke: frontend (vitest) ==" -ForegroundColor Cyan
    Set-Location (Join-Path $Root "frontend")
    npm test --silent
    Assert-StepSuccess

    Write-Host "== Rashid smoke: Playwright E2E ==" -ForegroundColor Cyan
    npm run e2e -- --reporter=line
    Assert-StepSuccess

    Write-Host "== Rashid smoke: live API ==" -ForegroundColor Cyan
    Set-Location $Root
    & "$Root\scripts\smoke-live-api.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    & "$Root\scripts\smoke-worker.ps1" -Action stop
}

Write-Host "Smoke finished." -ForegroundColor Green
