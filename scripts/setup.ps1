# Rashid Agent — first-time setup
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Rashid Agent setup" -ForegroundColor Cyan

& "$Root\scripts\setup-mirrors.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path "$Root\.env")) {
    Copy-Item "$Root\.env.example" "$Root\.env"
    Write-Host "Created .env from .env.example — add your API keys." -ForegroundColor Yellow
}

if (-not (Test-Path "$Root\.venv")) {
    Write-Host "Creating venv..." -ForegroundColor Yellow
    python -m venv .venv
}

& "$Root\.venv\Scripts\Activate.ps1"
pip install -e ".[dev]"

Write-Host "Setup complete. Next: .\scripts\infra-up.ps1 then .\scripts\dev.ps1" -ForegroundColor Green
