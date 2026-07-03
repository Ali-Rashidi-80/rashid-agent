# Rashid Agent — verify pip/npm/docker mirror connectivity
param(
    [switch]$SkipDocker
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Rashid Agent: verify mirrors" -ForegroundColor Cyan
$failed = 0

Write-Host "`n[pip]" -ForegroundColor Yellow
try {
    python -m pip install --dry-run certifi 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: pip reachable" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: pip dry-run failed" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  FAIL: python/pip not found" -ForegroundColor Red
    $failed++
}

Write-Host "`n[npm]" -ForegroundColor Yellow
if (Get-Command npm -ErrorAction SilentlyContinue) {
    $reg = npm config get registry 2>&1
    Write-Host "  registry: $reg"
    npm ping 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: npm ping" -ForegroundColor Green
    } else {
        Write-Host "  WARN: npm ping failed (optional until frontend)" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  SKIP: npm not installed" -ForegroundColor DarkGray
}

Write-Host "`n[docker]" -ForegroundColor Yellow
if (-not $SkipDocker) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK: docker daemon" -ForegroundColor Green
        } else {
            Write-Host "  FAIL: docker daemon not running" -ForegroundColor Red
            $failed++
        }
    } else {
        Write-Host "  FAIL: docker not installed" -ForegroundColor Red
        $failed++
    }
} else {
    Write-Host "  SKIP: -SkipDocker" -ForegroundColor DarkGray
}

Write-Host ""
if ($failed -gt 0) {
    Write-Host "Mirror verify: $failed check(s) failed. See docs/mirrors-iran-fa.md" -ForegroundColor Red
    exit 1
}
Write-Host "Mirror verify: all required checks passed." -ForegroundColor Green
exit 0
