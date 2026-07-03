# Rashid Agent — live API + worker for smoke / CI
param(
    [string]$ApiBase = "",
    [int]$TimeoutSec = 45
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $Root "backend"
$env:PYTHONPATH = $Backend
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://127.0.0.1:6380/0" }
$env:ARQ_REDIS_URL = if ($env:ARQ_REDIS_URL) { $env:ARQ_REDIS_URL } else { "redis://127.0.0.1:6380/1" }

$apiProc = $null
$workerProc = $null
$startedApi = $false
$startedWorker = $false
$apiPort = 8000

function Test-RashidHealth {
    param([string]$Url)
    try {
        $r = Invoke-RestMethod -Uri $Url -TimeoutSec 20
        return ($null -ne $r.postgres -and $null -ne $r.redis)
    } catch {
        return $false
    }
}

function Wait-ApiHealth {
    param([string]$Url, [int]$MaxSeconds)
    for ($i = 0; $i -lt $MaxSeconds; $i++) {
        if (Test-RashidHealth $Url) {
            return Invoke-RestMethod -Uri $Url -TimeoutSec 20
        }
        Start-Sleep -Seconds 1
    }
    return $null
}

try {
    if ($ApiBase) {
        $apiPort = ([uri]$ApiBase).Port
    }

    $healthUrl = if ($ApiBase) { "$ApiBase/api/v1/health" } else { "http://127.0.0.1:$apiPort/api/v1/health" }
    $health = $null
    if (Test-RashidHealth $healthUrl) {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 20
    }

    if (-not $health) {
        if (-not $ApiBase) {
            $apiPort = 18080 + (Get-Random -Maximum 50)
            $ApiBase = "http://127.0.0.1:$apiPort"
            $healthUrl = "$ApiBase/api/v1/health"
        }
        Write-Host "Starting temporary API on $ApiBase ..." -ForegroundColor Cyan
        $apiProc = Start-Process -FilePath "python" `
            -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $apiPort) `
            -WorkingDirectory $Backend `
            -PassThru -WindowStyle Hidden
        $startedApi = $true
        $health = Wait-ApiHealth -Url $healthUrl -MaxSeconds $TimeoutSec
        if (-not $health) {
            throw "API failed to become healthy at $ApiBase"
        }
    } else {
        if (-not $ApiBase) {
            $ApiBase = "http://127.0.0.1:$apiPort"
        }
    }

    if ($health.worker.status -ne "ok") {
        Write-Host "Starting temporary ARQ worker ..." -ForegroundColor Cyan
        $workerProc = Start-Process -FilePath "python" `
            -ArgumentList @("-m", "arq", "worker.settings.WorkerSettings") `
            -WorkingDirectory $Backend `
            -PassThru -WindowStyle Hidden
        $startedWorker = $true
        Start-Sleep -Seconds 4
        $health = Wait-ApiHealth -Url $healthUrl -MaxSeconds 25
        if (-not $health) {
            throw "API health lost after starting worker"
        }
    }

    if ($health.status -ne "ok") {
        $coreOk = $health.postgres.status -eq "ok" -and $health.redis.status -eq "ok"
        if (-not $coreOk) {
            throw "API unhealthy: $($health | ConvertTo-Json -Compress)"
        }
        Write-Warning "Worker status: $($health.worker.status)"
    } else {
        Write-Host "Health OK (postgres + redis + worker)" -ForegroundColor Green
    }

    try {
        Invoke-RestMethod -Uri "$ApiBase/api/v1/tools/repo-map" -TimeoutSec 5 | Out-Null
        throw "Expected repo-map without path to fail"
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 400) {
            throw "Expected 400 from repo-map without path, got: $($_.Exception.Message)"
        }
    }

    $tmpProject = Join-Path $env:TEMP "rashid-smoke-$(Get-Random)"
    New-Item -ItemType Directory -Force -Path $tmpProject | Out-Null
    $pathBody = @{ path = $tmpProject } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$ApiBase/api/v1/project/path" -ContentType "application/json" -Body $pathBody | Out-Null

    $sessionBody = @{ project_path = $tmpProject; mode = "ask"; title = "smoke" } | ConvertTo-Json
    $session = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/v1/sessions" -ContentType "application/json" -Body $sessionBody
    if (-not $session.id) {
        throw "Session create failed"
    }

    Write-Host "Live API smoke OK ($ApiBase)" -ForegroundColor Green
}
catch {
    Write-Error $_
    exit 1
}
finally {
    if ($startedWorker -and $workerProc -and -not $workerProc.HasExited) {
        Stop-Process -Id $workerProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($startedApi -and $apiProc -and -not $apiProc.HasExited) {
        Stop-Process -Id $apiProc.Id -Force -ErrorAction SilentlyContinue
    }
}
