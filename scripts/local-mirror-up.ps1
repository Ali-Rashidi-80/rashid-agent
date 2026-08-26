# Rashid Agent — build/start local DR mirror containers (rashid-mirror-*)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Rashid Agent: local-mirror-up" -ForegroundColor Cyan

if (-not (Test-Path ".env.local-mirror")) {
    if (Test-Path ".env.local-mirror.example") {
        Copy-Item ".env.local-mirror.example" ".env.local-mirror"
        Write-Host "Created .env.local-mirror from example - edit passwords before production use." -ForegroundColor Yellow
    } else {
        Write-Error "Missing .env.local-mirror and .env.local-mirror.example"
    }
}

$env:DOCKER_BUILDKIT = "1"
docker compose -p rashid-mirror -f docker-compose.local-mirror.yml --env-file .env.local-mirror build
if ($LASTEXITCODE -ne 0) { Write-Error "mirror build failed" }

docker compose -p rashid-mirror -f docker-compose.local-mirror.yml --env-file .env.local-mirror up -d
if ($LASTEXITCODE -ne 0) { Write-Error "mirror up failed" }

Write-Host "Mirror containers: rashid-mirror-db|redis|api|worker|web" -ForegroundColor Green
Write-Host 'API http://127.0.0.1:8001  Web http://127.0.0.1:3001 (ports from .env.local-mirror)' -ForegroundColor Green
