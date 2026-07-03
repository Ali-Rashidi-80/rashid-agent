# Rashid Agent — start postgres + redis via docker compose
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Rashid Agent: infra-up (postgres + redis)" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker not found. Install Docker Desktop and retry."
}

docker compose up -d postgres redis
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up failed"
}

Write-Host "Waiting for healthy services..." -ForegroundColor Yellow
$maxWait = 90
$elapsed = 0
while ($elapsed -lt $maxWait) {
    $ps = docker compose ps --format json 2>$null | ConvertFrom-Json
    $healthy = @($ps | Where-Object { $_.Health -eq "healthy" -or $_.State -eq "running" })
    if ($healthy.Count -ge 2) {
        Write-Host "Infrastructure ready." -ForegroundColor Green
        exit 0
    }
    Start-Sleep -Seconds 3
    $elapsed += 3
}

Write-Host "WARN: services may still be starting. Check: docker compose ps" -ForegroundColor Yellow
