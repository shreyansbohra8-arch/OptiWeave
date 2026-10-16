"""ML Analytics page."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from config import settings
from ml.predictor import model_status
from ml.train_model import train_and_save
from ui.components import clear_model_cache, read_json, show_badge


def render_analytics() -> None:
    st.header("ML Analytics")
    ok, msg = model_status()
    show_badge("Model ready" if ok else "Model not available", "ok" if ok else "warn")
    st.caption(msg)
    with st.expander("Regenerate dataset and retrain", expanded=not ok):
        st.write("Regenerates the 60 benchmark programs, re-runs all six strategies on each, rebuilds the "
                 "labelled dataset and retrains the Random Forest (deterministic, seed "
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
    st.warning(ev["note"] + f" (In-sample training accuracy: {ev['final_model_training_accuracy_in_sample']:.3f}.)")

    st.subheader("Optimization performance (mean instruction reduction %)")
    op = ev["optimization_performance"]
    rows = [{"selector": k, "mean %": v["mean_reduction_pct"], "median %": v["median_reduction_pct"]}
            for k, v in op.items() if isinstance(v, dict)]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.write(f"ML vs S6 per program - better: {op['ml_beats_s6_programs']}, equal: {op['ml_ties_s6_programs']}, "
             f"worse: {op['ml_loses_to_s6_programs']}. The oracle is an upper bound, not a deployable predictor.")

    left, right = st.columns(2)
    with left:
        st.subheader("Confusion matrix (held-out)")
        cm, labels = np.array(ev["confusion_matrix"]), ev["labels"]
        fig, ax = plt.subplots(figsize=(4.5, 4))
        ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(labels)), labels)
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
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.barh(imp.index, imp.values, color="#2f6fed")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    st.subheader("Selected-strategy (label) distribution")
    st.bar_chart(pd.Series(ev["label_distribution"], name="programs"))
    st.caption("Strategies that never win under the instruction-count objective (e.g. S2) have no samples.")
    with st.expander("Classification report"):
        st.dataframe(pd.DataFrame(ev["classification_report"]).T)
    if settings.DATASET_CSV.exists():
        with st.expander("Dataset (CSV)"):
            st.dataframe(pd.read_csv(settings.DATASET_CSV), hide_index=True)
