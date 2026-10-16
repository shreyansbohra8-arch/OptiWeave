"""Write benchmark tables, JSON summary, Markdown report and charts."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from benchmarking.metrics import summarize  # noqa: E402
from config import settings  # noqa: E402
from utils.file_utils import atomic_write_text  # noqa: E402


def _fmt(v, digits: int = 2) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def plot_mean_reduction(summary: dict, path: Path) -> None:
    labels = ["Unoptimized", "Fixed S6", "ML-selected"]
    vals = [summary["mean_reduction_pct"][k] or 0 for k in ("unoptimized", "fixed_s6", "ml_selected")]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(labels, vals, color=["#9aa5b1", "#2f6fed", "#1fa971"])
    ax.bar_label(bars, fmt="%.2f")
    ax.set_ylabel("Mean instruction reduction (%)")
    ax.set_title("Mean IR instruction reduction")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_by_category(summary: dict, path: Path) -> None:
    cats = list(summary["by_category"])
    if not cats:
        return
    x = np.arange(len(cats))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x - w / 2, [summary["by_category"][c]["fixed_s6"] for c in cats], w, label="Fixed S6", color="#2f6fed")
    ax.bar(x + w / 2, [summary["by_category"][c]["ml_selected"] for c in cats], w, label="ML-selected", color="#1fa971")
    ax.set_xticks(x)
    ax.set_xticklabels(cats, rotation=25, ha="right")
    ax.set_ylabel("Mean instruction reduction (%)")
    ax.set_title("Reduction by program category")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_strategy_distribution(summary: dict, path: Path) -> None:
    counts = summary["predicted_strategy_counts"]
    if not counts:
        return
    keys = sorted(counts)
    fig, ax = plt.subplots(figsize=(5.5, 4))
    bars = ax.bar(keys, [counts[k] for k in keys], color="#7a5cf0")
    ax.bar_label(bars)
    ax.set_title("ML-selected strategy distribution")
    ax.set_ylabel("Programs")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def markdown_report(summary: dict, df) -> str:
    m, md, t = summary["mean_reduction_pct"], summary["median_reduction_pct"], summary["timing"]
    v = summary["ml_vs_s6"]
    lines = [
        "# OptiWeave Benchmark Report", "",
        "All numbers below were produced by running the implementation "
        "(`python -m benchmarking.benchmark_runner`).", "",
        f"- Programs benchmarked successfully: **{summary['programs_ok']} / {summary['programs_total']}**",
        f"- Programs compiled with GCC (all three variants): **{summary['gcc_compiled_programs']}**",
        f"- IR-equivalence failures: **{len(summary['ir_equivalence_failures'])}**; "
        f"GCC output mismatches: **{len(summary['gcc_output_mismatches'])}**", "",
        "## Instruction reduction (primary, deterministic metric)", "",
        "| Version | Mean reduction % | Median reduction % |", "|---|---|---|",
        f"| Unoptimized | 0.00 | 0.00 |",
        f"| Fixed S6 (CF+CP+DCE+CSE) | {_fmt(m['fixed_s6'])} | {_fmt(md['fixed_s6'])} |",
        f"| ML-selected | {_fmt(m['ml_selected'])} | {_fmt(md['ml_selected'])} |", "",
        f"ML vs S6 per program: better **{v['ml_better']}**, equal **{v['equal']}**, worse **{v['ml_worse']}**.", "",
        "ML predictions for corpus programs are the *group-held-out* cross-validation predictions, "
        "so the ML row is not inflated by training on the same programs.", "",
        "## Execution time (secondary metric)", "",
        f"- Programs with reliable timing (all variants >= {settings.MIN_RELIABLE_RUNTIME_S * 1000:.0f} ms median): "
        f"{t['programs_with_reliable_timing']}",
        f"- Programs excluded from timing statistics: {t['programs_without_reliable_timing']}",
        f"- Median speed-up, fixed S6 vs unoptimized: {_fmt(t['median_speedup_fixed_s6_vs_unoptimized'], 3)}",
        f"- Median speed-up, ML vs unoptimized: {_fmt(t['median_speedup_ml_vs_unoptimized'], 3)}", "",
        "Timing = wall-clock of the compiled executable (monotonic `perf_counter`, median of repeated "
        "runs, GCC `-O0`). Most corpus programs finish in about a millisecond, which is dominated by "
        "process start-up, so only heavy workloads are reported.", "",
        "## Reduction by category (mean %)", "", "| Category | Fixed S6 | ML-selected |", "|---|---|---|",
    ]
    for c, d in summary["by_category"].items():
        lines.append(f"| {c} | {_fmt(d['fixed_s6'])} | {_fmt(d['ml_selected'])} |")
    lines += ["", "## Interpretation", "",
              "S6 contains every other strategy's passes, so under the instruction-count objective it can "
              "never do worse than another strategy; the ML selector can at best tie it. "
              "Differences between ML and S6 therefore measure ML prediction error, not a missed "
              "opportunity of S6. See docs/BENCHMARK_METHODOLOGY.md.", ""]
    if summary["programs_failed"]:
        lines += ["## Failures / exclusions", ""]
        lines += [f"- {f['program_id']}: {f['error']}" for f in summary["programs_failed"]]
    return "\n".join(lines) + "\n"


def write_reports(records: list) -> dict:
    """Write CSV, JSON, Markdown and PNG outputs; returns the summary dict."""
    from benchmarking.benchmark_runner import records_to_dataframe
    settings.ensure_directories()
    summary = summarize(records)
    df = records_to_dataframe(records)
    atomic_write_text(settings.BENCHMARK_RESULTS_CSV, df.to_csv(index=False))
    atomic_write_text(settings.BENCHMARK_SUMMARY_JSON, json.dumps(summary, indent=2))
    atomic_write_text(settings.REPORTS_DIR / "benchmark_report.md", markdown_report(summary, df))
    if summary["programs_ok"]:
        plot_mean_reduction(summary, settings.REPORTS_DIR / "mean_reduction.png")
        plot_by_category(summary, settings.REPORTS_DIR / "reduction_by_category.png")
        plot_strategy_distribution(summary, settings.REPORTS_DIR / "strategy_distribution.png")
    return summary
