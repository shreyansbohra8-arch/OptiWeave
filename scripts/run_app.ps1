# Launches the Streamlit application (does NOT retrain the model).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path "models\optiweave_rf.joblib")) {
    Write-Warning "No trained model found. Run scripts\train_model.ps1 first (the app still starts, ML mode will explain what is missing)."
}
& $py -m streamlit run app.py
