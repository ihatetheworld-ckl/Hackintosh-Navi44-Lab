# Reviewed: CPU-only runner, no upstream scripts, no installation or GPU calls.
param([Parameter(Mandatory=$true)][string]$PythonExe)
$ErrorActionPreference = 'Stop'
$labRoot = $PSScriptRoot
$oldTmp = $env:TMP
$oldTemp = $env:TEMP
try {
    $env:TMP = Join-Path $labRoot 'tmp'
    $env:TEMP = $env:TMP
    & $PythonExe -I -B (Join-Path $labRoot 'run_offline.py')
    if ($LASTEXITCODE -ne 0) { throw "Offline tests failed: $LASTEXITCODE" }
} finally {
    $env:TMP = $oldTmp
    $env:TEMP = $oldTemp
}
