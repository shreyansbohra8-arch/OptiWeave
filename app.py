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
from ui.compiler_view import (init_state, render_compiler_explorer, render_generated_code,
                              render_source_editor)
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
    c3.metric("Latest S6 mean reduction", f"{summary['mean_reduction_pct']['fixed_s6']:.2f}%" if summary else "n/a")
    show_badge(msg, "ok" if ok else "warn")
    if not ok:
        st.code("python -m ml.train_model")
    if summary:
        m, v = summary["mean_reduction_pct"], summary["ml_vs_s6"]
        st.markdown(f"**Latest benchmark:** {summary['programs_ok']} programs - mean reduction: "
                    f"S6 {m['fixed_s6']:.2f}%, ML {m['ml_selected']:.2f}% "
                    f"(ML better/equal/worse than S6: {v['ml_better']}/{v['equal']}/{v['ml_worse']}).")


def render_about() -> None:
    st.header("Documentation / About")
    st.markdown("""
**Architecture.** `.ow` source -> lexer -> recursive-descent parser (AST) -> semantic analyzer (symbol table,
types) -> three-address code -> basic blocks / CFG -> 10 features -> Random Forest -> optimizer pipeline ->
C code generator -> GCC `-O0` -> benchmark and reports. See `docs/ARCHITECTURE.md`.

**Optimization passes.** CF folds constants (and constant branches). CP is a global data-flow analysis.
DCE uses backward liveness plus unreachable-code and redundant-jump removal. CSE is local value numbering
with copy forwarding. Execution order is always CF -> CSE -> CP -> DCE, repeated to a fixed point
(max 10 rounds).

**Dataset and ML.** 60 generated programs in 6 categories (30 families x 2 variants). Every program is run
through all six strategies; the label is the strategy with the fewest instructions (ties: fewer passes).
Evaluation is GroupKFold by family, with majority, fixed-S6 and oracle comparisons.

**Benchmark limitations.** Instruction count is the primary metric; most programs are too short for
reliable timing; the corpus is small and synthetic; S6 is a superset of all strategies, so ML can at best tie
it on instruction count.
""")
    st.subheader("The six strategies")
    st.table([{"Strategy": s.id, "Passes": s.label,
               "Meaning": ", ".join(PASS_FULL_NAMES[p] for p in s.ordered_passes)} for s in STRATEGIES.values()])


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
