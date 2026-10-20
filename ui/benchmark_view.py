"""Benchmark Comparison page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from benchmarking.benchmark_runner import load_timing_workloads, run_corpus
from benchmarking.report_generator import write_reports
from compiler.code_generator import find_gcc
from config import settings
from ml.dataset_generator import load_programs
from optimizer.optimization_pipeline import describe_passes, run_strategy
from optimizer.strategies import FIXED_STRATEGY, cost_aware_score
from ui.components import get_predictor, read_json, show_badge
from ui.compiler_view import current_frontend, current_opt_result, init_state, render_active_program_banner
from utils.exceptions import IncompatibleModelError, ModelNotFoundError


def _render_active_program_benchmark() -> None:
    """Show Unoptimized vs ML vs fixed S10 for the program compiled in Source Editor."""
    st.subheader("Active program")
    init_state()
    render_active_program_banner()
    fe = current_frontend()
    if fe is None or not fe.ok:
        st.info("Compile a valid program in **Source Editor** to compare that file here. "
                "The corpus table below is a saved run of 135+ programs, not the file in the editor.")
        return
    opt = current_opt_result()
    s10 = run_strategy(fe.ir, FIXED_STRATEGY)
    orig = fe.ir.instruction_count
    rows = [{
        "variant": "Unoptimized",
        "strategy": "none",
        "passes": "—",
        "instructions": orig,
        "reduction %": 0.0,
        "cost-aware score": 0.0,
        "used for this program": False,
    }]
    if opt is not None:
        rows.append({
            "variant": "ML / Optimization Lab",
            "strategy": opt.strategy_id,
            "passes": describe_passes(opt.strategy_id),
            "instructions": opt.optimized_count,
            "reduction %": round(opt.reduction_pct, 2),
            "cost-aware score": round(cost_aware_score(opt.reduction_pct, opt.strategy_id), 2),
            "used for this program": True,
        })
        c1, c2, c3 = st.columns(3)
        c1.metric("Selected strategy", opt.strategy_id)
        c2.metric("Selected reduction", f"{opt.reduction_pct:.2f}%")
        c3.metric(f"Fixed {FIXED_STRATEGY} baseline", f"{s10.reduction_pct:.2f}%")
        if opt.strategy_id == FIXED_STRATEGY:
            st.caption(f"The model chose **{FIXED_STRATEGY}** for this file (all passes).")
        else:
            st.caption(
                f"This file uses **{opt.strategy_id}**, not {FIXED_STRATEGY}. "
                f"{FIXED_STRATEGY} is shown only as the all-passes baseline."
            )
    else:
        st.warning("No ML / Lab result yet for this file. Compile again in Source Editor.")
    rows.append({
        "variant": f"Fixed {FIXED_STRATEGY} (baseline)",
        "strategy": FIXED_STRATEGY,
        "passes": describe_passes(FIXED_STRATEGY),
        "instructions": s10.optimized_count,
        "reduction %": round(s10.reduction_pct, 2),
        "cost-aware score": round(cost_aware_score(s10.reduction_pct, FIXED_STRATEGY), 2),
        "used for this program": bool(opt is not None and opt.strategy_id == FIXED_STRATEGY),
    })
    st.dataframe(pd.DataFrame(rows), hide_index=True)


def render_benchmark() -> None:
    st.header("Benchmark Comparison")
    _render_active_program_benchmark()
    st.subheader("Saved corpus (all programs)")
    st.markdown(
        "These numbers are from the **last corpus run** (unoptimized vs **fixed S10** vs **ML-selected** "
        "on every benchmark file). They do **not** change when you compile a different example in Source Editor."
    )
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
        st.info("No corpus benchmark results yet.")
        return
    m = summary["mean_reduction_pct"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Unoptimized (corpus mean)", "0.00%")
    c2.metric("Fixed S10 (corpus mean)", f"{m['fixed_s10']:.2f}%")
    c3.metric("ML-selected (corpus mean)", f"{m['ml_selected']:.2f}%")

    if "mean_cost_aware_score" in summary:
        cs = summary["mean_cost_aware_score"]
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Unoptimized (cost-aware)", "0.00")
        sc2.metric("Fixed S10 (cost-aware score)", f"{cs['fixed_s10']:.2f}")
        sc3.metric("ML-selected (cost-aware score)", f"{cs['ml_selected']:.2f}")

    v = summary["ml_vs_s10"]
    st.write(f"ML vs S10 per program (cost-aware score): better **{v['ml_better_score']}**, "
             f"equal **{v['equal_score']}**, worse **{v['ml_worse_score']}**. "
             f"Programs benchmarked: {summary['programs_ok']}/{summary['programs_total']}; "
             f"GCC-compiled (all variants): {summary['gcc_compiled_programs']}.")
    st.write(f"ML vs S10 per program (instruction reduction): better **{v['ml_better_reduction']}**, "
             f"equal **{v['equal_reduction']}**, worse **{v['ml_worse_reduction']}**.")
    if summary["ir_equivalence_failures"] or summary["gcc_output_mismatches"]:
        st.error(f"Equivalence problems: {summary['ir_equivalence_failures']} {summary['gcc_output_mismatches']}")
    t = summary["timing"]
    st.subheader("Execution time")
    if t["programs_with_reliable_timing"]:
        st.write(f"{t['programs_with_reliable_timing']} program(s) ran long enough for reliable timing. "
                 f"Median speed-up vs unoptimized - S10: {t['median_speedup_fixed_s10_vs_unoptimized']:.3f}x, "
                 f"ML: {t['median_speedup_ml_vs_unoptimized']:.3f}x.")
    else:
        st.write("No program ran long enough for reliable timing; timing is not reported.")
    st.caption(t["note"])
    for img, cap in (("mean_reduction.png", "Mean reduction"), ("reduction_by_category.png", "By category"),
                     ("cost_aware_score.png", "Cost-aware score comparison"),
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
            "- **Instruction reduction %** = (original - optimized) / original × 100 on IR instructions "
            "(labels excluded).\n"
            "- **Cost-aware score** = instruction reduction % − 0.5 × sum of pass costs. Lighter strategies "
            "can outperform heavier ones when the extra passes produce little benefit.\n"
            "- Corpus ML predictions are *group-held-out* cross-validation predictions, not in-sample ones.\n"
            "- S10 runs all 6 passes (CF+SR+COP+CSE+CP+DCE) and has the highest cost; ML can beat it "
            "by choosing a lighter strategy with similar reduction.\n"
            "- GCC runs at `-O0`; tiny programs run in about a millisecond and are excluded from timing.\n"
            "- The 135-program corpus is synthetic; results do not generalise to real software.")
