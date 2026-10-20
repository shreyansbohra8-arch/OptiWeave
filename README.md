# OptiWeave: A Learning-Based Framework for Program-Aware Compiler Optimization

Compiler Design Lab project (BCSE307P). A complete, runnable compiler pipeline for a small C-like language
(`.ow`) with **six** real IR optimisation passes, a Random Forest that chooses one of **ten** optimisation pipelines per
program using a **cost-aware** evaluation metric, C code generation, GCC (`-O0`) benchmarking, and a Streamlit interface.
Everything reported here is produced by running the code; nothing is hard-coded.

## 1. Problem statement
Fixed optimisation pipelines apply the same passes to every program. Some passes do nothing for some programs, yet
every pass costs compile time. OptiWeave asks whether static features of the IR/CFG can predict which pipeline to use,
using a **cost-aware score** that penalises heavier strategies so lighter, equally-effective pipelines can win.

## 2. Objectives
* Implement a full front end (lexer, recursive-descent parser with error recovery, AST, semantic analysis, 3AC, basic blocks, CFG).
* Implement **six** optimization passes: Constant Folding, Strength Reduction, Copy Propagation, Common Subexpression Elimination, Constant Propagation, and Dead Code Elimination.
* Implement **iterative/fixed-point** optimization — passes re-run until no further changes occur.
* Define **ten** strategies (S1-S10), extract **fourteen** features (10 raw + 4 ratio-based), label a **135-program** corpus using cost-aware scoring.
* Train/evaluate a Random Forest *without* family-level leakage and compare with majority / S10 / oracle baselines.
* Run hyperparameter comparison across Random Forest, Gradient Boosting, and Decision Tree configurations.
* Generate C, compile with GCC `-O0`, verify equivalence, benchmark honestly, present it in a UI.

## 3. Architecture
```
.ow -> Lexer -> Parser(AST) -> Semantic analyzer -> 3AC -> Basic blocks -> CFG -> 14 features
    -> Random Forest -> strategy S1..S10 -> optimizer (CF, SR, COP, CSE, CP, DCE) -> C code -> GCC -O0 -> benchmark/reports/UI
```
Details: `docs/ARCHITECTURE.md`.

## 4. Optimization Passes
| Pass | Abbreviation | Description |
|------|-------------|-------------|
| Constant Folding | CF | Evaluates constant expressions at compile time |
| Strength Reduction | SR | Replaces expensive ops with cheaper equivalents (e.g., `x * 2` → `x + x`, power-of-2 multiplies → shifts) |
| Copy Propagation | COP | Replaces `x = y; use(x)` with `use(y)`, enabling further optimizations |
| Common Subexpression Elimination | CSE | Removes redundant recomputations of the same expression within a basic block |
| Constant Propagation | CP | Replaces variable uses with their known constant values (global data-flow) |
| Dead Code Elimination | DCE | Removes instructions whose results are never used (liveness analysis) |

## 5. Optimization Strategies
| Strategy | Passes | Use Case |
|----------|--------|----------|
| S1 | CF | Minimal: only fold constants |
| S2 | CF + CP | Constants + propagation |
| S3 | CF + DCE | Constants + dead code removal |
| S4 | CF + CP + DCE | Constants + propagation + dead code |
| S5 | CF + CP + CSE | Constants + propagation + common subexpressions |
| S6 | CF + CP + DCE + CSE | Original "full" pipeline |
| S7 | CF + SR | Constants + strength reduction |
| S8 | CF + SR + DCE | Strength + dead code |
| S9 | CF + COP + CP + DCE | Copy propagation + constants + dead code |
| S10 | CF + SR + COP + CP + DCE + CSE | All passes (heaviest, highest compile cost) |

## 6. ML Features (14)
| # | Feature | Type | Description |
|---|---------|------|-------------|
| 1 | instruction_count | raw | Non-label IR instructions |
| 2 | arithmetic_op_count | raw | Binary +, -, *, /, % instructions |
| 3 | branch_count | raw | Conditional jumps |
| 4 | loop_count | raw | CFG back edges |
| 5 | basic_block_count | raw | Number of basic blocks |
| 6 | constant_expression_count | raw | BinOp/UnOp with all-constant operands |
| 7 | duplicate_expression_count | raw | Repeated expressions in same block |
| 8 | assignment_count | raw | Plain copy/assignment instructions |
| 9 | distinct_variable_count | raw | Distinct user variables |
| 10 | cfg_edge_count | raw | Edges in the control-flow graph |
| 11 | constant_expression_ratio | derived | constant_expression_count / instruction_count |
| 12 | duplicate_expression_ratio | derived | duplicate_expression_count / instruction_count |
| 13 | assignment_ratio | derived | assignment_count / instruction_count |
| 14 | branch_ratio | derived | branch_count / instruction_count |

## 7. Cost-Aware Evaluation
The key innovation: instead of measuring only instruction-count reduction (where the all-passes S10 always ties or wins),
we use a **cost-aware score**:

```
score = instruction_reduction_% − 0.5 × sum(pass_costs)
```

This penalises heavier strategies, so the ML selector can legitimately beat S10 by choosing a lighter pipeline
that achieves similar reduction with lower compile-time overhead.

## 8. Supported language
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

## 9. Folder structure
```
OptiWeave/
  app.py  README.md  requirements*.txt  .gitignore  .env.example  LICENSE
  config/ (settings)      compiler/ (tokens lexer ast_nodes parser symbol_table semantic_analyzer ir ir_generator
                                      basic_blocks cfg code_generator pipeline cli)
  optimizer/ (6 passes, strategies, optimization_pipeline)
  ml/ (feature_extractor program_templates dataset_generator evaluation train_model predictor model_metadata)
  benchmarking/ (benchmark_runner metrics equivalence report_generator)
  ui/ (components compiler_view optimization_view benchmark_view analytics_view)   utils/   tests/ (16 files + conftest)
  data/{benchmarks,datasets,results}   models/   examples/   outputs/{generated_c,generated_ir,reports}   scripts/   docs/
```

## 10. Technology stack
Python 3.11/3.12, scikit-learn, pandas, NumPy, Matplotlib, joblib, Streamlit, pytest, GCC (MinGW-w64/MSYS2 on Windows). No internet or API keys needed at run time.

## 11. Windows setup, training and launch (PowerShell)
```powershell
cd OptiWeave
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m pip install --upgrade pip
pip install -r requirements-dev.txt   # requirements.txt + pytest

python -m ml.train_model              # generates 135 programs + dataset, evaluates, trains, saves model
python -m ml.train_model --search     # also runs hyperparameter comparison across model configs
python -m pytest -q                   # automated tests (165 tests)
python -m benchmarking.benchmark_runner   # optional: regenerates data/results and outputs/reports
python -m streamlit run app.py        # launch the UI
```
Without activating the environment: `.\.venv\Scripts\python.exe -m pytest -q`.
Scripts (no activation needed): `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`, then `scripts\train_model.ps1`,
`scripts\run_tests.ps1`, `scripts\run_app.ps1`. **One-command demo** (sets up if needed, trains only if no model exists, launches the app):
`powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1`.
Command-line compiler: `python -m compiler.cli examples\mixed.ow --gcc` (`--strategy S1..S10|auto`, `--save`).
Dataset only: `python -m ml.dataset_generator`. Retrain without regenerating: `python -m ml.train_model --reuse-dataset`.

## 12. GCC installation and verification (Windows)
1. Install MSYS2 from https://www.msys2.org. 2. Open the **UCRT64** shell and run `pacman -S mingw-w64-ucrt-x86_64-gcc`.
3. Add `C:\msys64\ucrt64\bin` to your PATH (or set `OPTIWEAVE_GCC=C:\msys64\ucrt64\bin\gcc.exe`). 4. Open a new terminal: `gcc --version`.
If GCC is missing the app and benchmark say so and report instruction metrics only.

## 13. Example output
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

## 14. Benchmark methodology
Summarised in `docs/BENCHMARK_METHODOLOGY.md`. Primary metric: IR instruction reduction; cost-aware scoring penalises
heavier pipelines; correctness verified by an IR interpreter and by comparing GCC outputs; timing is secondary and reported only when reliable.

## 15. Tests
`python -m pytest -q` — **165 tests** across lexer, parser, semantics, IR, CFG, **six** passes (including copy propagation & strength reduction),
features, strategies (S1–S10), ML pipeline, code generation, benchmarking and integration (incl. a Streamlit smoke test).
Tests needing GCC are skipped with a stated reason if GCC is absent.

## 16. Known limitations
Small language; CSE is block-local; DCE uses plain liveness (misses self-feeding dead accumulators); names must be globally unique;
int is 64-bit wrap-around; synthetic 135-program corpus written by the author; only a handful of timing workloads;
the PowerShell scripts were written for Windows but could not be executed in the Linux development
environment (the Python commands they wrap were run there).

## 17. Troubleshooting
`docs/TROUBLESHOOTING.md` (execution policy, missing GCC, missing model, ports).

## 18. VS Code and GitHub
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
