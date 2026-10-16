# One-command demo: sets up the environment if needed, trains ONLY if no model exists, starts the app.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path ".venv\Scripts\python.exe")) { & (Join-Path $PSScriptRoot "setup.ps1") }
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path "models\optiweave_rf.joblib")) {
    Write-Host "No model found - training once..."
    & $py -m ml.train_model
}
& $py -m streamlit run app.py
