# OptiWeave: A Learning-Based Framework for Program-Aware Compiler Optimization

Compiler Design Lab project (BCSE307P). A complete, runnable compiler pipeline for a small C-like language
(`.ow`) with four real IR optimisation passes, a Random Forest that chooses one of six optimisation pipelines per
program, C code generation, GCC (`-O0`) benchmarking, and a Streamlit interface. Everything reported here is
produced by running the code; nothing is hard-coded.

## 1. Problem statement
Fixed optimisation pipelines apply the same passes to every program. Some passes do nothing for some programs, yet
every pass costs compile time. OptiWeave asks whether static features of the IR/CFG can predict which pipeline to use.

## 2. Objectives
* Implement a full front end (lexer, recursive-descent parser, AST, semantic analysis, 3AC, basic blocks, CFG).
* Implement Constant Folding, Constant Propagation, Dead Code Elimination and Common Subexpression Elimination.
* Define six strategies (S1-S6), extract ten features, label a 60-program corpus by actually running the optimiser.
* Train/evaluate a Random Forest *without* family-level leakage and compare with majority / S6 / oracle baselines.
* Generate C, compile with GCC `-O0`, verify equivalence, benchmark honestly, present it in a UI.

## 3. Architecture
```
.ow -> Lexer -> Parser(AST) -> Semantic analyzer -> 3AC -> Basic blocks -> CFG -> 10 features
    -> Random Forest -> strategy S1..S6 -> optimiser (CF, CSE, CP, DCE) -> C code -> GCC -O0 -> benchmark/reports/UI
```
Details: `docs/ARCHITECTURE.md`.

## 4. Features
Language: `int/float/bool`, declarations, assignment, `if/else`, `while`, `print`, arithmetic/relational/logical
(short-circuit) operators, comments, located errors. Compiler: IR with explicit branch targets, dominator-based loop
detection, DOT/Graphviz CFG, IR interpreter, C backend with checked division. ML: deterministic dataset generation,
GroupKFold evaluation, versioned model + metadata with compatibility checks. UI: dashboard, editor, explorer,
optimisation lab, code view, benchmarks, analytics, docs.

## 5. Technology stack
Python 3.11/3.12, scikit-learn, pandas, NumPy, Matplotlib, joblib, Streamlit, pytest, GCC (MinGW-w64/MSYS2 on Windows). No internet or API keys needed at run time.

## 6. Folder structure
```
OptiWeave/
  app.py  README.md  requirements*.txt  .gitignore  .env.example  LICENSE
  config/ (settings)      compiler/ (tokens lexer ast_nodes parser symbol_table semantic_analyzer ir ir_generator
                                      basic_blocks cfg code_generator pipeline cli)
  optimizer/ (4 passes, strategies, optimization_pipeline)
  ml/ (feature_extractor program_templates dataset_generator evaluation train_model predictor model_metadata)
  benchmarking/ (benchmark_runner metrics equivalence report_generator)
  ui/ (components compiler_view optimization_view benchmark_view analytics_view)   utils/   tests/ (16 files + conftest)
  data/{benchmarks,datasets,results}   models/   examples/   outputs/{generated_c,generated_ir,reports}   scripts/   docs/
```
(`compiler/pipeline.py`, `compiler/cli.py` and `ml/program_templates.py` were added to the proposed structure to keep modules small.
`outputs/generated_ir/` is reserved for IR dumps you save yourself.)

## 7. Supported language
See `docs/LANGUAGE_GRAMMAR.md`. Example:
```c
int i = 0;
int s = 0;
while (i < 10) {
    int p = i * 3 + 1;
    int q = i * 3 + 1;     // redundant
    if (p % 2 == 0 && i > 2) { s = s + p; } else { s = s + q; }
    i = i + 1;
}
print(s);
```

## 8-14. Windows setup, training and launch (PowerShell)
```powershell
cd OptiWeave
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m pip install --upgrade pip
pip install -r requirements-dev.txt   # requirements.txt + pytest

python -m ml.train_model              # generates 60 programs + dataset, evaluates, trains, saves model
python -m pytest -q                   # automated tests
python -m benchmarking.benchmark_runner   # optional: regenerates data/results and outputs/reports
python -m streamlit run app.py        # launch the UI
```
Without activating the environment: `.\.venv\Scripts\python.exe -m pytest -q`.
Scripts (no activation needed): `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`, then `scripts\train_model.ps1`,
`scripts\run_tests.ps1`, `scripts\run_app.ps1`. **One-command demo** (sets up if needed, trains only if no model exists, launches the app):
`powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1`.
Command-line compiler: `python -m compiler.cli examples\mixed.ow --gcc` (`--strategy S1..S6|auto`, `--save`).
Dataset only: `python -m ml.dataset_generator`. Retrain without regenerating: `python -m ml.train_model --reuse-dataset`.

## 16. GCC installation and verification (Windows)
1. Install MSYS2 from https://www.msys2.org. 2. Open the **UCRT64** shell and run `pacman -S mingw-w64-ucrt-x86_64-gcc`.
3. Add `C:\msys64\ucrt64\bin` to your PATH (or set `OPTIWEAVE_GCC=C:\msys64\ucrt64\bin\gcc.exe`). 4. Open a new terminal: `gcc --version`.
If GCC is missing the app and benchmark say so and report instruction metrics only.

## 17-18. Example and output format
`python -m compiler.cli examples\constants.ow --gcc` (excerpt of a real run):
```
ML-selected strategy: S4 (confidence 0.94)
Strategy S4: Constant Folding -> Constant Propagation -> Dead Code Elimination
Passes that changed the IR: CF, CP, DCE
== Optimized IR ==
    print 55
Instructions: 11 -> 1 (90.91% reduction)
Equivalence check: passed (identical output)
GCC compilation OK. Program output:
55
```
Confidence values can differ slightly across scikit-learn versions.

## 19. Benchmark methodology
Summarised in `docs/BENCHMARK_METHODOLOGY.md`. Primary metric: IR instruction reduction; correctness verified by an IR
interpreter and by comparing GCC outputs; timing is secondary and reported only when reliable.

### Results of the run performed while developing (Linux, Python 3.12, GCC 13.3, scikit-learn 1.8)
Regenerate on your machine with the commands above; numbers there are authoritative.
* Corpus: 60 programs, 30 families; labels S1 24, S3 6, S4 20, S5 2, S6 8 (S2 never wins - see `docs/OPTIMIZATION_PASSES.md`).
* Group-held-out accuracy 0.667, macro-F1 0.443, majority-class baseline accuracy 0.400.
* Mean instruction reduction: oracle 26.93 %, **fixed S6 26.93 %**, **ML (held-out) 21.60 %**, majority class 0.00 %.
  ML was never better than S6 (50 equal, 11 worse in the 61-program GCC benchmark, which includes one extra timing workload).
  This is expected: S6 includes every pass, so on this objective ML can at best tie it.
* GCC: all 61 programs compiled in all three variants, 0 IR-equivalence failures, 0 output mismatches.
* Timing: only the 40M-iteration `examples/heavy_loop.ow` ran long enough for reliable timing (median speed-up vs unoptimized about 1.27x for S6 and 1.29x for ML);
  a single data point, not a general claim.

## 15. Tests
`python -m pytest -q` - 155 tests across lexer, parser, semantics, IR, CFG, the four passes, features, strategies, ML pipeline,
code generation, benchmarking and integration (incl. a Streamlit smoke test). Tests needing GCC are skipped with a stated reason if GCC is absent.
Result of the final run in the development environment: **155 passed, 0 skipped** (GCC available).

## 20. Known limitations
Small language; CSE is block-local; DCE uses plain liveness (misses self-feeding dead accumulators); names must be globally unique;
int is 64-bit wrap-around; synthetic 60-program corpus written by the author; ML cannot beat S6 on the instruction-count objective;
only one timing workload; the PowerShell scripts were written for Windows but could not be executed in the Linux development
environment (the Python commands they wrap were run there).

## 21. Troubleshooting
`docs/TROUBLESHOOTING.md` (execution policy, missing GCC, missing model, ports).

## 22. VS Code and GitHub
```powershell
code .                                   # open in VS Code; choose the .venv interpreter (Ctrl+Shift+P -> Python: Select Interpreter)
git init
git add .
git commit -m "OptiWeave: learning-based compiler optimization framework"
git branch -M main
git remote add origin https://github.com/<your-user>/OptiWeave.git
git push -u origin main
```
`.gitignore` excludes the venv, caches, executables and the trained model (`models/*.joblib`, retrain with one command).

Other docs: `docs/LANGUAGE_GRAMMAR.md`, `docs/OPTIMIZATION_PASSES.md`, `docs/ML_METHODOLOGY.md`, `docs/BENCHMARK_METHODOLOGY.md`,
`docs/DEMO_GUIDE.md`, `docs/VIVA_QUESTIONS.md`.
