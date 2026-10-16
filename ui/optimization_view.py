"""Optimization Lab page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from benchmarking.equivalence import check_equivalence
from ml.feature_extractor import extract_features
from optimizer.optimization_pipeline import describe_passes, run_strategy
from optimizer.strategies import PASS_FULL_NAMES, STRATEGIES, STRATEGY_IDS
from ui.components import code_panel, features_table, get_predictor, show_badge
from ui.compiler_view import current_frontend, init_state
from utils.exceptions import IncompatibleModelError, ModelNotFoundError


def render_optimization_lab() -> None:
    st.header("Optimization Lab")
    init_state()
    fe = current_frontend()
    if fe is None or not fe.ok:
        st.info("Compile a valid program in **Source Editor** first.")
        return
    features = extract_features(fe.ir, fe.cfg)
    mode = st.radio("Strategy selection", ["Automatic (ML Random Forest)", "Manual"], horizontal=True)
    strategy_id = None
    if mode.startswith("Automatic"):
        try:
            pred = get_predictor().predict(features)
        except (ModelNotFoundError, IncompatibleModelError) as exc:
            show_badge("Model unavailable", "err")
            st.error(str(exc))
            st.code("python -m ml.train_model")
            return
        strategy_id = pred.strategy_id
        c1, c2 = st.columns(2)
        c1.metric("Predicted strategy", f"{pred.strategy_id}  ({STRATEGIES[pred.strategy_id].label})")
        c2.metric("Confidence", f"{pred.confidence * 100:.1f}%")
        st.bar_chart(pd.Series(pred.probabilities, name="probability"))
    else:
        strategy_id = st.selectbox("Strategy", STRATEGY_IDS,
                                   format_func=lambda s: f"{s}: {STRATEGIES[s].label}", index=5)
    res = run_strategy(fe.ir, strategy_id)
    st.session_state["opt_result"] = res
    st.markdown(f"**Pipeline:** {describe_passes(strategy_id)}  \n"
                f"**Passes that changed the IR:** {', '.join(res.passes_applied) or 'none'}  \n"
                f"**Fixed-point rounds:** {res.iterations}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Original instructions", res.original_count)
    m2.metric("Optimized instructions", res.optimized_count)
    m3.metric("Reduction", f"{res.reduction_pct:.2f}%")
    eq = check_equivalence(fe.ir, res.optimized)
    if eq.checked and eq.equivalent:
        show_badge("Behaviour preserved (IR interpreter output identical)", "ok")
    elif not eq.checked:
        show_badge(eq.detail, "warn")
    else:
        show_badge("Behaviour CHANGED - " + eq.detail, "err")
    st.subheader("Effect of each pass")
    st.dataframe(pd.DataFrame([{"round": r.iteration, "pass": f"{r.pass_name} ({PASS_FULL_NAMES[r.pass_name]})",
                                "instructions before": r.instructions_before,
                                "instructions after": r.instructions_after, "rewrites": r.rewrites,
                                "IR changed": r.changed} for r in res.records]),
                 hide_index=True)
    left, right = st.columns(2)
    with left:
        st.subheader("Original IR")
        code_panel(res.original.to_text(numbered=True))
    with right:
        st.subheader("Optimized IR")
        code_panel(res.optimized.to_text(numbered=True))
    with st.expander("Features used for prediction"):
        st.dataframe(features_table(features))
