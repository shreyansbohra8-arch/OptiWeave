"""ML Analytics page."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from config import settings
from ml.feature_extractor import extract_features
from ml.predictor import model_status
from ml.train_model import train_and_save
from optimizer.strategies import STRATEGIES
from ui.components import clear_model_cache, features_table, get_predictor, read_json, show_badge
from ui.compiler_view import current_frontend, current_opt_result, init_state, render_active_program_banner
from utils.exceptions import IncompatibleModelError, ModelNotFoundError


def _render_active_program_prediction() -> None:
    st.subheader("Active program")
    init_state()
    render_active_program_banner()
    fe = current_frontend()
    if fe is None or not fe.ok:
        st.info("Compile a valid program in **Source Editor** to see the model’s prediction for that file. "
                "The charts below are held-out evaluation of the 135-program corpus.")
        return
    features = extract_features(fe.ir, fe.cfg)
    opt = current_opt_result()
    try:
        pred = get_predictor().predict(features)
    except (ModelNotFoundError, IncompatibleModelError) as exc:
        show_badge("Model unavailable", "err")
        st.error(str(exc))
        return
    used = opt.strategy_id if opt is not None else pred.strategy_id
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted strategy", pred.strategy_id)
    c2.metric("Confidence", f"{pred.confidence * 100:.1f}%")
    c3.metric("Applied on this file", used)
    st.caption(f"Pipeline: {STRATEGIES[pred.strategy_id].label}. "
               "S10 is only used when the model (or a manual Lab choice) selects it.")
    st.bar_chart(pd.Series(pred.probabilities, name="probability"))
    with st.expander("Features for this program"):
        st.dataframe(features_table(features))


def render_analytics() -> None:
    st.header("ML Analytics")
    ok, msg = model_status()
    show_badge("Model ready" if ok else "Model not available", "ok" if ok else "warn")
    st.caption(msg)
    _render_active_program_prediction()
    st.subheader("Corpus evaluation")
    st.caption("Held-out metrics for the trained Random Forest on the 135-program dataset. "
               "These do not change when you compile a different example.")
    with st.expander("Regenerate dataset and retrain", expanded=not ok):
        st.write("Regenerates the 135 benchmark programs, re-runs all ten strategies on each, rebuilds the "
                 "labelled dataset using cost-aware scoring and retrains the Random Forest (deterministic, seed "
                 f"{settings.RANDOM_SEED}).")
        if st.button("Regenerate & retrain"):
            with st.spinner("Generating dataset and training..."):
                train_and_save(regenerate=True)
                clear_model_cache()
            st.success("Done.")
            st.rerun()
    ev = read_json(settings.ML_EVALUATION_JSON)
    if ev is None:
        st.info("No evaluation results yet. Train the model first.")
        return
    st.caption(ev["evaluation"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Held-out accuracy", f"{ev['accuracy']:.3f}")
    c2.metric("Macro F1", f"{ev['macro_f1']:.3f}")
    c3.metric("Majority baseline acc.", f"{ev['majority_baseline_accuracy']:.3f}")
    c4.metric("Balanced accuracy", f"{ev['balanced_accuracy']:.3f}")
    if "note" in ev:
        st.warning(ev["note"] + f" (In-sample training accuracy: {ev['final_model_training_accuracy_in_sample']:.3f}.)")

    st.subheader("Optimization performance")
    op = ev["optimization_performance"]
    rows = []
    for k, v in op.items():
        if isinstance(v, dict) and "mean_reduction_pct" in v:
            row = {"selector": k, "mean reduction %": v["mean_reduction_pct"],
                   "median reduction %": v["median_reduction_pct"]}
            if "mean_cost_aware_score" in v:
                row["mean cost-aware score"] = v["mean_cost_aware_score"]
                row["median cost-aware score"] = v["median_cost_aware_score"]
            rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.write(f"ML vs S10 per program (cost-aware score) - better: {op.get('ml_beats_s10_programs', 0)}, "
             f"equal: {op.get('ml_ties_s10_programs', 0)}, "
             f"worse: {op.get('ml_loses_to_s10_programs', 0)}. The oracle is an upper bound, not a deployable predictor.")

    left, right = st.columns(2)
    with left:
        st.subheader("Confusion matrix (held-out)")
        cm, labels = np.array(ev["confusion_matrix"]), ev["labels"]
        fig, ax = plt.subplots(figsize=(5.5, 5))
        ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True (best strategy)")
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, cm[i, j], ha="center", va="center", color="black" if cm[i, j] < cm.max() / 2 else "white")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    with right:
        st.subheader("Feature importance")
        imp = pd.Series(ev["feature_importance"]).sort_values()
        fig, ax = plt.subplots(figsize=(5, max(4, len(imp) * 0.3)))
        ax.barh(imp.index, imp.values, color="#2f6fed")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    st.subheader("Selected-strategy (label) distribution")
    st.bar_chart(pd.Series(ev["label_distribution"], name="programs"))
    st.caption("Labels are chosen by cost-aware scoring (instruction reduction penalised by pass cost). "
               "Lighter strategies win when heavier passes add little benefit.")
    with st.expander("Classification report"):
        st.dataframe(pd.DataFrame(ev["classification_report"]).T)

    if "hyperparameter_comparison" in ev:
        with st.expander("Hyperparameter comparison"):
            hp = ev["hyperparameter_comparison"]
            hp_rows = [{"config": k, **v} for k, v in hp.items()]
            st.dataframe(pd.DataFrame(hp_rows), hide_index=True)

    if settings.DATASET_CSV.exists():
        with st.expander("Dataset (CSV)"):
            st.dataframe(pd.read_csv(settings.DATASET_CSV), hide_index=True)
