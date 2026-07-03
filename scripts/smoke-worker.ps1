# Start/stop ARQ worker for local smoke + pytest
param(
    [ValidateSet("start", "stop")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $Root "backend"
$PidFile = Join-Path $Root "backend\data\smoke-worker.pid"

$env:PYTHONPATH = $Backend
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://127.0.0.1:6380/0" }
$env:ARQ_REDIS_URL = if ($env:ARQ_REDIS_URL) { $env:ARQ_REDIS_URL } else { "redis://127.0.0.1:6380/1" }

if ($Action -eq "start") {
    if (Test-Path $PidFile) {
        $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
            Write-Host "ARQ worker already running (pid $oldPid)" -ForegroundColor Yellow
            exit 0
        }
    }
    $proc = Start-Process -FilePath "python" `
        -ArgumentList @("-m", "arq", "worker.settings.WorkerSettings") `
        -WorkingDirectory $Backend `
        -PassThru -WindowStyle Hidden
    New-Item -ItemType Directory -Force -Path (Split-Path $PidFile) | Out-Null
    $proc.Id | Set-Content $PidFile
    Start-Sleep -Seconds 4
    Write-Host "ARQ worker started (pid $($proc.Id))" -ForegroundColor Green
    exit 0
}

if (Test-Path $PidFile) {
    $pidText = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($pidText) {
        Stop-Process -Id $pidText -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}
Write-Host "ARQ worker stopped" -ForegroundColor Green
