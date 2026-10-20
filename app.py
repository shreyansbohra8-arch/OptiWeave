"""OptiWeave - Streamlit application entry point.

Run with:  python -m streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from config import settings
from ml.predictor import model_status
from optimizer.strategies import PASS_FULL_NAMES, STRATEGIES
from ui.analytics_view import render_analytics
from ui.benchmark_view import render_benchmark
from ui.components import PIPELINE_DOT, benchmark_program_count, inject_css, read_json, show_badge
from ui.compiler_view import (current_opt_result, init_state, render_active_program_banner,
                              render_compiler_explorer, render_generated_code, render_source_editor)
from ui.optimization_view import render_optimization_lab

st.set_page_config(page_title="OptiWeave", page_icon="\U0001F9F5", layout="wide")


def render_dashboard() -> None:
    st.title("OptiWeave")
    st.subheader("A Learning-Based Framework for Program-Aware Compiler Optimization")
    st.write("A complete compiler pipeline for a small C-like language that selects an optimization "
             "pipeline per program with a Random Forest, applies real IR optimizations, emits C and "
             "benchmarks the result with GCC.")
    st.graphviz_chart(PIPELINE_DOT)
    ok, msg = model_status()
    c1, c2, c3 = st.columns(3)
    c1.metric("Benchmark programs", benchmark_program_count())
    c2.metric("Model status", "Ready" if ok else "Not trained")
    summary = read_json(settings.BENCHMARK_SUMMARY_JSON)
    c3.metric("Latest S10 mean reduction", f"{summary['mean_reduction_pct'].get('fixed_s10', summary['mean_reduction_pct'].get('fixed_s6', 0.0)):.2f}%" if summary else "n/a")
    show_badge(msg, "ok" if ok else "warn")
    if not ok:
        st.code("python -m ml.train_model")
    if summary:
        m = summary["mean_reduction_pct"]
        s_fixed = m.get("fixed_s10", m.get("fixed_s6", 0.0))
        fixed_name = "S10" if "fixed_s10" in m else "S6"
        v = summary.get("ml_vs_s10", summary.get("ml_vs_s6", {}))
        b = v.get("ml_better_score", v.get("ml_better", 0))
        eq = v.get("equal_score", v.get("equal", 0))
        w = v.get("ml_worse_score", v.get("ml_worse", 0))
        st.markdown(f"**Latest benchmark:** {summary['programs_ok']} programs - mean reduction: "
                    f"{fixed_name} {s_fixed:.2f}%, ML {m['ml_selected']:.2f}% "
                    f"(ML better/equal/worse: {b}/{eq}/{w}).")


def render_about() -> None:
    st.header("Documentation / About")
    init_state()
    render_active_program_banner()
    opt = current_opt_result()
    if opt is not None:
        st.info(f"The file compiled in Source Editor is using **{opt.strategy_id}** "
                f"({STRATEGIES[opt.strategy_id].label}). **S10** is the all-passes baseline, "
                "not the default for every program.")
    else:
        st.caption("This page is reference documentation. Compile a program in Source Editor "
                   "to see which strategy that file is using.")
    st.markdown("""
**Architecture.** `.ow` source -> lexer -> recursive-descent parser (AST with panic-mode error recovery) ->
semantic analyzer (symbol table, types) -> three-address code -> basic blocks / CFG -> 14 features ->
Random Forest -> optimizer pipeline -> C code generator -> GCC `-O0` -> benchmark and reports. See `docs/ARCHITECTURE.md`.

**Optimization passes.** CF folds constants (and constant branches). SR performs strength reduction.
COP propagates copies. CP is a global data-flow analysis. DCE uses backward liveness plus unreachable-code
and redundant-jump removal. CSE is local value numbering with copy forwarding. Execution order follows
the strategy pipeline, repeated to a fixed point (max 10 rounds).

**Dataset and ML.** 135 generated programs in 9 categories (45 families x 3 variants). Every program is run
through all ten strategies; the label is the strategy with the best cost-aware objective score (ties: fewer passes).
Evaluation is GroupKFold by family, with majority, fixed-S10 and oracle comparisons.

**Benchmark methodology.** Cost-aware score combines deterministic IR instruction-count reduction with
pass-execution cost penalties, enabling lighter targeted strategies to outscore heavy pipelines. Timing is
measured over dedicated compute-heavy workloads when runtime exceeds reliability thresholds.
""")
    st.subheader("The ten strategies")
    active = opt.strategy_id if opt is not None else None
    st.dataframe([
        {
            "Strategy": s.id,
            "Passes": s.label,
            "Meaning": ", ".join(PASS_FULL_NAMES[p] for p in s.ordered_passes),
            "Role": (
                "Selected for the active program"
                if s.id == active
                else ("All-passes baseline (not auto-applied)" if s.id == "S10" else "")
            ),
        }
        for s in STRATEGIES.values()
    ], hide_index=True)


PAGES = {
    "Dashboard": render_dashboard,
    "Source Editor": render_source_editor,
    "Compiler Explorer": render_compiler_explorer,
    "Optimization Lab": render_optimization_lab,
    "Generated Code": render_generated_code,
    "Benchmark Comparison": render_benchmark,
    "ML Analytics": render_analytics,
    "Documentation / About": render_about,
}

inject_css()
init_state()
with st.sidebar:
    st.title("OptiWeave")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.caption("BCSE307P Compiler Design Lab")
PAGES[page]()
