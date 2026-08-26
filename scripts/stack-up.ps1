# Rashid Agent — start full Docker stack (postgres, redis, migrate, api, worker, web)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Rashid Agent: stack-up (profile full)" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker not found. Install Docker Desktop and retry."
}

if (-not (Test-Path ".env")) {
    Write-Host "WARN: .env missing — copy .env.example to .env and fill secrets." -ForegroundColor Yellow
}

$env:DOCKER_BUILDKIT = "1"
docker compose --profile full up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose --profile full up failed"
}

Write-Host "Waiting for API health..." -ForegroundColor Yellow
$maxWait = 180
$elapsed = 0
while ($elapsed -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) {
            Write-Host "Full stack ready. Web: http://127.0.0.1:3000  API: http://127.0.0.1:8000" -ForegroundColor Green
            exit 0
        }
    } catch {
        # still starting
    }
    Start-Sleep -Seconds 3
    $elapsed += 3
}

Write-Host "WARN: stack may still be starting. Check: docker compose --profile full ps" -ForegroundColor Yellow
