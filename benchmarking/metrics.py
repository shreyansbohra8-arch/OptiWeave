"""Summary statistics for benchmark records."""
from __future__ import annotations

import statistics
from collections import defaultdict

from optimizer.optimization_pipeline import instruction_reduction_pct  # re-exported

__all__ = ["instruction_reduction_pct", "summarize", "median_or_none"]


def median_or_none(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def summarize(records: list) -> dict:
    """Aggregate :class:`BenchmarkRecord` objects into a JSON-friendly summary."""
    ok = [r for r in records if r.status == "ok"]
    failed = [r for r in records if r.status != "ok"]
    s6 = [r.variants["fixed_s6"].reduction_pct for r in ok]
    ml = [r.variants["ml_selected"].reduction_pct for r in ok]
    summary = {
        "programs_total": len(records),
        "programs_ok": len(ok),
        "programs_failed": [{"program_id": r.program_id, "error": r.error} for r in failed],
        "mean_reduction_pct": {"unoptimized": 0.0, "fixed_s6": _mean(s6), "ml_selected": _mean(ml)},
        "median_reduction_pct": {"unoptimized": 0.0, "fixed_s6": median_or_none(s6),
                                 "ml_selected": median_or_none(ml)},
        "ml_vs_s6": {
            "ml_better": sum(m > s + 1e-9 for m, s in zip(ml, s6)),
            "equal": sum(abs(m - s) <= 1e-9 for m, s in zip(ml, s6)),
            "ml_worse": sum(m < s - 1e-9 for m, s in zip(ml, s6)),
        },
        "ir_equivalence_failures": [r.program_id for r in ok if r.equivalence_checked and not r.ir_equivalent],
        "ir_equivalence_not_checked": [r.program_id for r in ok if not r.equivalence_checked],
        "gcc_compiled_programs": sum(1 for r in ok if all(v.compile_ok for v in r.variants.values())),
        "gcc_output_mismatches": [r.program_id for r in ok if r.gcc_outputs_match is False],
        "predicted_strategy_counts": {},
    }
    for r in ok:
        summary["predicted_strategy_counts"][r.ml_strategy] = \
            summary["predicted_strategy_counts"].get(r.ml_strategy, 0) + 1

    by_cat: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"fixed_s6": [], "ml_selected": []})
    for r in ok:
        by_cat[r.category]["fixed_s6"].append(r.variants["fixed_s6"].reduction_pct)
        by_cat[r.category]["ml_selected"].append(r.variants["ml_selected"].reduction_pct)
    summary["by_category"] = {c: {k: _mean(v) for k, v in d.items()} for c, d in sorted(by_cat.items())}

    # timing: only programs where every variant was measured reliably
    ratios_s6, ratios_ml = [], []
    reliable = 0
    for r in ok:
        times = {k: v.median_time_s for k, v in r.variants.items()}
        if all(v.timing_reliable for v in r.variants.values()) and all(t for t in times.values()):
            reliable += 1
            ratios_s6.append(times["unoptimized"] / times["fixed_s6"])
            ratios_ml.append(times["unoptimized"] / times["ml_selected"])
    summary["timing"] = {
        "programs_with_reliable_timing": reliable,
        "programs_without_reliable_timing": len(ok) - reliable,
        "median_speedup_fixed_s6_vs_unoptimized": median_or_none(ratios_s6),
        "median_speedup_ml_vs_unoptimized": median_or_none(ratios_ml),
        "note": "Speed-up = unoptimized median time / variant median time. Runs shorter than the "
                "reliability threshold are excluded (dominated by process start-up noise).",
    }
    return summary
