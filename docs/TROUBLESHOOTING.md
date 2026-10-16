# Troubleshooting

| Problem | Fix |
|---|---|
| `.\.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled` | Session-only: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. Or skip activation: `.\.venv\Scripts\python.exe -m pytest -q`. The `scripts\*.ps1` files already call the venv Python directly: `powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1`. |
| `py -3.12` not found | Install Python 3.12 from python.org (tick "Add to PATH") or use `python -m venv .venv` with 3.11+. |
| `No trained model at ...` | `python -m ml.train_model` |
| `Model was trained with a different feature set` / version error | Retrain: `python -m ml.train_model` |
| GCC was not found | Install MSYS2 (https://www.msys2.org), open the **UCRT64** shell, run `pacman -S mingw-w64-ucrt-x86_64-gcc`, add `C:\msys64\ucrt64\bin` to PATH, reopen the terminal, check `gcc --version`. Or set `OPTIWEAVE_GCC` to the full path of `gcc.exe`. GCC tests are skipped (with a reason) when GCC is missing. |
| `ModuleNotFoundError` | Run commands from the project root and with the venv: `pip install -r requirements.txt`. |
| Streamlit port busy | `python -m streamlit run app.py --server.port 8502` |
| Benchmark reports "timing not reliable" | Expected for short programs; use `examples/heavy_loop.ow` or increase workloads. |
| Antivirus blocks generated `.exe` | Executables are built in temporary directories and deleted; allow-list the temp folder if needed. |
