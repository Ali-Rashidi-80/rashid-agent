# Rashid Agent — raw Docker stack for Chabokan/remote (no compose profiles)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Rashid Agent: chabokan-stack-up" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Write-Error "Create .env from .env.example (fill POSTGRES_PASSWORD and SECRETS_ENCRYPTION_KEY; examples stay empty)."
}

$env:DOCKER_BUILDKIT = "1"
$env:RASHID_COMPOSE_ENV_FILE = ".env"
docker compose -f docker-compose.chabokan.yml --env-file .env build
if ($LASTEXITCODE -ne 0) { Write-Error "chabokan build failed" }

docker compose -f docker-compose.chabokan.yml --env-file .env up -d
if ($LASTEXITCODE -ne 0) { Write-Error "chabokan up failed" }

Write-Host "Containers: rashid-chabokan-postgres|redis|api|worker|web (+ migrate once)" -ForegroundColor Green
Write-Host "See docs/deployment.md for TLS / Telegram webhook / managed DB notes." -ForegroundColor Cyan
