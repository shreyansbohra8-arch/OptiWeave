# Runs the automated test-suite.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& (Join-Path $root ".venv\Scripts\python.exe") -m pytest -q @args
