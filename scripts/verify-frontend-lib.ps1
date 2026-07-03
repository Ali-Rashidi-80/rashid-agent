# Ensure frontend lib sources are present (not gitignored)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Lib = Join-Path $Root "frontend\src\lib"

$required = @(
  "agent-store.ts",
  "cn.ts",
  "session-api.ts",
  "theme-engine.tsx",
  "theme-script.tsx",
  "theme-store.ts"
)

$missing = @()
foreach ($file in $required) {
  if (-not (Test-Path (Join-Path $Lib $file))) {
    $missing += $file
  }
}

if ($missing.Count -gt 0) {
  Write-Error "Missing frontend lib files: $($missing -join ', ')"
}

Write-Host "frontend/src/lib OK ($($required.Count) core files)" -ForegroundColor Green
exit 0
