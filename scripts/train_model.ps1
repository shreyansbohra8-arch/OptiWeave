# Generates the benchmark corpus + dataset and trains the Random Forest.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& (Join-Path $root ".venv\Scripts\python.exe") -m ml.train_model @args
