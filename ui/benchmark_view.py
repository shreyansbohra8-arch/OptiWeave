"""Benchmark Comparison page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from benchmarking.benchmark_runner import load_timing_workloads, run_corpus
from benchmarking.report_generator import write_reports
from compiler.code_generator import find_gcc
from config import settings
from ml.dataset_generator import load_programs
from ui.components import get_predictor, read_json, show_badge
from utils.exceptions import IncompatibleModelError, ModelNotFoundError


def render_benchmark() -> None:
    st.header("Benchmark Comparison")
    st.markdown("Compares **unoptimized**, **fixed S6** (CF+CP+DCE+CSE) and the **ML-selected** strategy. "
                "The primary metric is deterministic IR instruction-count reduction; execution time is "
                "secondary and shown only when reliably measured.")
    summary = read_json(settings.BENCHMARK_SUMMARY_JSON)
    with st.expander("Run / re-run the benchmark", expanded=summary is None):
        gcc = find_gcc() is not None
        show_badge("GCC found" if gcc else "GCC not found - instruction metrics only", "ok" if gcc else "warn")
        repeats = st.slider("Timing repeats per executable", 1, 9, settings.TIMING_REPEATS)
        if st.button("Run benchmark on all programs"):
            try:
                predictor = get_predictor()
            except (ModelNotFoundError, IncompatibleModelError) as exc:
                st.error(str(exc))
                st.code("python -m ml.train_model")
            else:
                progs = load_programs()
                if not progs:
                    st.error("No benchmark programs found. Train the model first (it generates them).")
                else:
                    oof = None
                    if settings.OOF_PREDICTIONS_CSV.exists():
                        o = pd.read_csv(settings.OOF_PREDICTIONS_CSV)
                        oof = dict(zip(o["program_id"], o["ml_strategy"]))
                    with st.spinner("Benchmarking..."):
                        recs = run_corpus(progs + load_timing_workloads(), predictor, oof, gcc, repeats)
                        summary = write_reports(recs)
                    st.success("Benchmark finished.")
    if summary is None:
        st.info("No benchmark results yet.")
        return
    m = summary["mean_reduction_pct"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Unoptimized", "0.00%")
    c2.metric("Fixed S6 (mean reduction)", f"{m['fixed_s6']:.2f}%")
    c3.metric("ML-selected (mean reduction)", f"{m['ml_selected']:.2f}%")
    v = summary["ml_vs_s6"]
    st.write(f"ML vs S6 per program: better **{v['ml_better']}**, equal **{v['equal']}**, worse **{v['ml_worse']}**. "
             f"Programs benchmarked: {summary['programs_ok']}/{summary['programs_total']}; "
             f"GCC-compiled (all variants): {summary['gcc_compiled_programs']}.")
    if summary["ir_equivalence_failures"] or summary["gcc_output_mismatches"]:
        st.error(f"Equivalence problems: {summary['ir_equivalence_failures']} {summary['gcc_output_mismatches']}")
    t = summary["timing"]
    st.subheader("Execution time")
    if t["programs_with_reliable_timing"]:
        st.write(f"{t['programs_with_reliable_timing']} program(s) ran long enough for reliable timing. "
                 f"Median speed-up vs unoptimized - S6: {t['median_speedup_fixed_s6_vs_unoptimized']:.3f}x, "
                 f"ML: {t['median_speedup_ml_vs_unoptimized']:.3f}x.")
    else:
        st.write("No program ran long enough for reliable timing; timing is not reported.")
    st.caption(t["note"])
    for img, cap in (("mean_reduction.png", "Mean reduction"), ("reduction_by_category.png", "By category"),
                     ("strategy_distribution.png", "ML-selected strategy distribution")):
        p = settings.REPORTS_DIR / img
        if p.exists():
            st.image(str(p), caption=cap)
    if settings.BENCHMARK_RESULTS_CSV.exists():
        df = pd.read_csv(settings.BENCHMARK_RESULTS_CSV)
        st.subheader("Per-program results")
        st.dataframe(df, hide_index=True)
        st.download_button("Download results CSV", df.to_csv(index=False), file_name="benchmark_results.csv")
    with st.expander("Metric definitions and limitations"):
        st.markdown(
            "- **Instruction reduction %** = (original - optimized) / original x 100 on IR instructions "
            "(labels excluded).\n"
            "- Corpus ML predictions are *group-held-out* cross-validation predictions, not in-sample ones.\n"
            "- S6 is a superset of every other strategy, so ML can at best tie it on this metric.\n"
            "- GCC runs at `-O0`; tiny programs run in about a millisecond and are excluded from timing.\n"
            "- The 60-program corpus is small and synthetic; results do not generalise to real software.")
