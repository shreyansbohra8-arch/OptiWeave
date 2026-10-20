# Faculty Demo Guide (about 10 minutes)

Prerequisites: `scripts\run_demo.ps1` (or the manual commands in README) has been run once and `python -m pytest -q` is green.

1. **Dashboard** - show the pipeline diagram, 135 benchmark programs, model status "Ready", latest benchmark summary.
2. **Source Editor** - load `mixed.ow`, press *Compile*. Then load `invalid_program.ow`: show the located type error and that compilation stops. Mention the parser's **error recovery** (reports multiple errors in one pass).
3. **Compiler Explorer** - tokens, AST, symbol table, original 3AC (point at `t1 = b * 2`-style code), basic blocks, CFG with the red loop back-edge, the fourteen features (10 raw + 4 ratio-based).
4. **Optimization Lab** - *Automatic* mode: predicted strategy + confidence + probabilities. Walk through the per-pass table, original vs optimized IR, the reduction %. Switch to *Manual* and pick S1, then S7 (strength reduction), then S10 (all passes) to compare. Point out the **iterative/fixed-point** optimization (passes re-run until no further changes).
5. **Generated Code** - show the C, press *Compile and run with GCC*, point out the identical output.
6. **Benchmark Comparison** - unoptimized vs S10 vs ML. Show both **instruction reduction** and **cost-aware score** metrics. ML-vs-S10 counts: ML beats S10 on cost-aware score because it chooses lighter strategies. Show timing results from heavy workload programs.
7. **ML Analytics** - held-out accuracy vs majority baseline, confusion matrix (10×10), feature importance (14 features), label distribution; mention group-aware evaluation and the in-sample warning. Show hyperparameter comparison table if available.
8. **Terminal** - `python -m pytest -q` (165 tests) and `python -m compiler.cli examples/constants.ow --gcc`.

Be ready to explain:
- **Why ML beats S10**: cost-aware scoring penalises heavy strategies, so lighter pipelines with similar reduction win.
- **Six optimization passes**: CF, SR (strength reduction), COP (copy propagation), CSE, CP, DCE.
- **Ten strategies** (S1-S10) covering different pass combinations.
- The limitations section of the README.
