# Full test runner — delegates to smoke-test.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$Root\smoke-test.ps1"
exit $LASTEXITCODE
