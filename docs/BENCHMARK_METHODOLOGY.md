# Benchmark Methodology

Three versions are compared for every program: **unoptimized** (original IR), **fixed S10** (all passes), and **ML-selected**.

1. **Primary metric (deterministic)**: IR instruction-count reduction `(orig - opt) / orig * 100`, 0 when `orig = 0`.
2. **Cost-aware score**: `instruction_reduction_% - 0.5 × sum(pass_costs)`. This penalises heavier strategies so
   lighter pipelines with similar reduction can legitimately outscore S10.
3. **Correctness first**: each optimised IR is compared with the original by the IR interpreter (same printed output and
   run-time error status). Generated C is compiled with `gcc -O0 -std=c11 -fwrapv`; outputs of all three executables must match.
   Programs whose original exceeds the interpreter step limit are marked "equivalence not checked" (GCC output comparison still applies).
4. **ML selection without leakage**: for corpus programs the ML strategy is the *out-of-fold* prediction from the group-aware
   cross-validation. `--final-model` uses the in-sample final model instead (optimistic; labelled as such in the CSV).
   Programs outside the corpus (e.g., timing workloads) use the final model legitimately.
5. **Timing (secondary)**: `time.perf_counter` around each process run, `TIMING_REPEATS` runs, median reported; compilation time
   recorded separately. A variant is "reliable" only when its median >= 10 ms; speed-ups are computed only for programs where all
   three variants are reliable. Most corpus programs run in ~1 ms (dominated by process start-up) and are excluded.
   Heavy-computation examples (`large_accumulator.ow`, `nested_heavy.ow`, etc.) are included for reliable timing data.
6. **Reporting**: failures and exclusions are listed; nothing is imputed. Outputs: `data/results/benchmark_results.csv`,
   `benchmark_summary.json`, `outputs/reports/benchmark_report.md` and PNG charts.

## Known limitations
* Fewer IR instructions does not guarantee a faster executable (and GCC runs at `-O0` on purpose).
* Synthetic 135-program corpus; handful of timing workloads.
* Cost-aware weights are heuristic; different weights could change strategy rankings.
* ML can beat S10 on the cost-aware objective by choosing lighter strategies.
