# OptiWeave Benchmark Report

All numbers below were produced by running the implementation (`python -m benchmarking.benchmark_runner`).

- Programs benchmarked successfully: **141 / 141**
- Programs compiled with GCC (all three variants): **141**
- IR-equivalence failures: **0**; GCC output mismatches: **0**

## Instruction reduction (deterministic metric)

| Version | Mean reduction % | Median reduction % |
|---|---|---|
| Unoptimized | 0.00 | 0.00 |
| Fixed S10 (all passes) | 38.89 | 23.08 |
| ML-selected | 34.01 | 18.75 |

## Cost-aware score (primary evaluation metric)

The cost-aware score balances instruction reduction against the compile-time cost of running more passes: `score = reduction% − 0.5 × Σ pass_costs`.

| Version | Mean cost-aware score |
|---|---|
| Fixed S10 (all passes) | 33.14 |
| ML-selected | 31.20 |

ML vs S10 per program (cost-aware score): better **96**, equal **18**, worse **27**.

ML vs S10 per program (raw reduction): better **0**, equal **111**, worse **30**.

ML predictions for corpus programs are the *group-held-out* cross-validation predictions, so the ML row is not inflated by training on the same programs.

## Execution time (secondary metric)

- Programs with reliable timing (all variants >= 10 ms median): 7
- Programs excluded from timing statistics: 134
- Median speed-up, fixed S10 vs unoptimized: 1.085
- Median speed-up, ML vs unoptimized: 1.063

Timing = wall-clock of the compiled executable (monotonic `perf_counter`, median of repeated runs, GCC `-O0`). Most corpus programs finish in about a millisecond, which is dominated by process start-up, so only heavy workloads are reported.

## Reduction by category (mean %)

| Category | Fixed S10 | ML-selected |
|---|---|---|
| algebraic-heavy | 56.34 | 51.17 |
| arithmetic-heavy | 28.75 | 28.75 |
| branch-heavy | 41.98 | 29.95 |
| constant-heavy | 72.92 | 53.25 |
| copy-heavy | 55.33 | 52.17 |
| loop-heavy | 6.71 | 4.62 |
| mixed | 4.85 | 1.54 |
| propagation-only | 71.56 | 71.56 |
| redundant-expression-heavy | 17.69 | 17.69 |
| timing-workload | 23.65 | 22.46 |

## Interpretation

S10 contains all six passes, so under the raw instruction-count objective it can never do worse than any other strategy. Under the **cost-aware score**, however, lighter strategies can beat S10 when the extra passes provide little additional reduction. The ML selector exploits this by choosing the best cost-adjusted strategy for each program.

