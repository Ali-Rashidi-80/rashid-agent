$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:PYTHONPATH = Join-Path $Root "backend"
Set-Location (Join-Path $Root "backend")
$ErrorActionPreference = "Continue"
python -m alembic upgrade head
$code = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
exit $code
