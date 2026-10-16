# Creates .venv, installs dependencies and checks for GCC.
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment (.venv)..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { py -3 -m venv .venv }
    } else {
        python -m venv .venv
    }
}
$py = Join-Path $root ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements-dev.txt

if (Get-Command gcc -ErrorAction SilentlyContinue) {
    gcc --version | Select-Object -First 1
} else {
    Write-Warning "GCC not found. Install MSYS2 + mingw-w64-ucrt-x86_64-gcc and add C:\msys64\ucrt64\bin to PATH (see README section 16)."
}
Write-Host "Setup complete. Next: scripts\train_model.ps1"
