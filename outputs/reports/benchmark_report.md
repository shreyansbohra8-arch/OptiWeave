# OptiWeave Benchmark Report

All numbers below were produced by running the implementation (`python -m benchmarking.benchmark_runner`).

- Programs benchmarked successfully: **61 / 61**
- Programs compiled with GCC (all three variants): **61**
- IR-equivalence failures: **0**; GCC output mismatches: **0**

## Instruction reduction (primary, deterministic metric)

| Version | Mean reduction % | Median reduction % |
|---|---|---|
| Unoptimized | 0.00 | 0.00 |
| Fixed S6 (CF+CP+DCE+CSE) | 26.92 | 8.33 |
| ML-selected | 21.67 | 0.00 |

ML vs S6 per program: better **0**, equal **50**, worse **11**.

ML predictions for corpus programs are the *group-held-out* cross-validation predictions, so the ML row is not inflated by training on the same programs.

## Execution time (secondary metric)

- Programs with reliable timing (all variants >= 10 ms median): 1
- Programs excluded from timing statistics: 60
- Median speed-up, fixed S6 vs unoptimized: 1.271
- Median speed-up, ML vs unoptimized: 1.290

Timing = wall-clock of the compiled executable (monotonic `perf_counter`, median of repeated runs, GCC `-O0`). Most corpus programs finish in about a millisecond, which is dominated by process start-up, so only heavy workloads are reported.

## Reduction by category (mean %)

| Category | Fixed S6 | ML-selected |
|---|---|---|
| arithmetic-heavy | 28.24 | 27.57 |
| branch-heavy | 41.55 | 17.50 |
| constant-heavy | 72.96 | 71.29 |
| loop-heavy | 4.62 | 0.00 |
| mixed | 4.85 | 3.85 |
| redundant-expression-heavy | 9.37 | 9.37 |
| timing-workload | 26.09 | 26.09 |

## Interpretation

S6 contains every other strategy's passes, so under the instruction-count objective it can never do worse than another strategy; the ML selector can at best tie it. Differences between ML and S6 therefore measure ML prediction error, not a missed opportunity of S6. See docs/BENCHMARK_METHODOLOGY.md.

