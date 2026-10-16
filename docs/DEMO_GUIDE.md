# Faculty Demo Guide (about 10 minutes)

Prerequisites: `scripts\run_demo.ps1` (or the manual commands in README) has been run once and `python -m pytest -q` is green.

1. **Dashboard** - show the pipeline diagram, 60 benchmark programs, model status "Ready", latest benchmark summary.
2. **Source Editor** - load `mixed.ow`, press *Compile*. Then load `invalid_program.ow`: show the located type error and that compilation stops.
3. **Compiler Explorer** - tokens, AST, symbol table, original 3AC (point at `t1 = b * 2`-style code), basic blocks, CFG with the red loop back-edge, the ten features.
4. **Optimization Lab** - *Automatic* mode: predicted strategy + confidence + probabilities. Walk through the per-pass table, original vs optimized IR, the reduction %. Switch to *Manual* and pick S1 then S6 to compare.
5. **Generated Code** - show the C, press *Compile and run with GCC*, point out the identical output.
6. **Benchmark Comparison** - unoptimized vs S6 vs ML, ML-vs-S6 counts, the honest statement that S6 is a superset (ML can only tie) and that most programs are too short for timing.
7. **ML Analytics** - held-out accuracy vs majority baseline, confusion matrix, feature importance, label distribution; mention group-aware evaluation and the in-sample warning.
8. **Terminal** - `python -m pytest -q` and `python -m compiler.cli examples/constants.ow --gcc`.

Be ready to explain: why S2 is never optimal, why ML cannot beat S6 on this metric, and the limitations section of the README.
