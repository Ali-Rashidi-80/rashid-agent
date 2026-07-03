# Rashid Agent — گام ۰.۱: configure Iran mirrors (Chabokan default)
param(
    [ValidateSet("chabokan", "arvan", "direct")]
    [string]$Profile = "chabokan"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$MirrorsDir = Join-Path $Root "config\mirrors"

Write-Host "Rashid Agent: setup mirrors (profile=$Profile)" -ForegroundColor Cyan

$envFile = Join-Path $MirrorsDir "$Profile.env"
if (-not (Test-Path $envFile)) {
    Write-Error "Mirror profile not found: $envFile"
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_ -split '=', 2
    if ($parts.Count -eq 2) {
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
        Write-Host "  env $name=$value"
    }
}

$pipDir = Join-Path $env:APPDATA "pip"
$pipIni = Join-Path $pipDir "pip.ini"
$pipTemplate = Join-Path $MirrorsDir "pip.ini.template"
if ($Profile -ne "direct" -and (Test-Path $pipTemplate)) {
    New-Item -ItemType Directory -Force -Path $pipDir | Out-Null
    Copy-Item $pipTemplate $pipIni -Force
    Write-Host "  pip.ini -> $pipIni" -ForegroundColor Green
}

$npmTemplate = Join-Path $MirrorsDir ".npmrc.template"
$frontendNpmrc = Join-Path $Root "frontend\.npmrc"
if ($Profile -ne "direct" -and (Test-Path $npmTemplate)) {
    $frontendDir = Join-Path $Root "frontend"
    if (-not (Test-Path $frontendDir)) {
        New-Item -ItemType Directory -Force -Path $frontendDir | Out-Null
    }
    Copy-Item $npmTemplate $frontendNpmrc -Force
    Write-Host "  frontend/.npmrc updated" -ForegroundColor Green
}

Write-Host ""
Write-Host "Docker Desktop: apply config/mirrors/daemon.json.template manually if needed." -ForegroundColor Yellow
Write-Host "Run: .\scripts\verify-mirrors.ps1" -ForegroundColor Yellow
