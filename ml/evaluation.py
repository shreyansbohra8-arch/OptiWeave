"""Group-aware evaluation of the strategy classifier and of its optimisation impact."""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeClassifier

from config import settings
from ml.feature_extractor import FEATURE_NAMES
from optimizer.strategies import FIXED_STRATEGY, STRATEGY_IDS, cost_aware_score

RF_PARAMS = {"n_estimators": 200, "random_state": settings.RANDOM_SEED, "n_jobs": 1}

# Candidate model configurations for hyperparameter comparison
MODEL_CONFIGS = {
    "rf_200": {"cls": RandomForestClassifier, "params": {"n_estimators": 200, "random_state": settings.RANDOM_SEED, "n_jobs": 1}},
    "rf_500": {"cls": RandomForestClassifier, "params": {"n_estimators": 500, "random_state": settings.RANDOM_SEED, "n_jobs": 1}},
    "rf_200_d10": {"cls": RandomForestClassifier, "params": {"n_estimators": 200, "max_depth": 10,
                   "random_state": settings.RANDOM_SEED, "n_jobs": 1}},
    "rf_200_leaf5": {"cls": RandomForestClassifier, "params": {"n_estimators": 200, "min_samples_leaf": 5,
                     "random_state": settings.RANDOM_SEED, "n_jobs": 1}},
    "gb_200": {"cls": GradientBoostingClassifier, "params": {"n_estimators": 200, "random_state": settings.RANDOM_SEED}},
    "dt_gini": {"cls": DecisionTreeClassifier, "params": {"random_state": settings.RANDOM_SEED}},
}


def make_model() -> RandomForestClassifier:
    return RandomForestClassifier(**RF_PARAMS)


def _majority(labels) -> str:
    counts = Counter(labels)
    top = max(counts.values())
    return sorted(k for k, v in counts.items() if v == top)[0]


def group_cross_validate(df: pd.DataFrame, n_splits: int = 5) -> tuple[dict, pd.DataFrame]:
    """GroupKFold by program *family* so near-identical variants never straddle train/test.

    Returns (metrics dict, out-of-fold prediction table).
    """
    groups = df["family"].to_numpy()
    n_groups = len(set(groups))
    n_splits = max(2, min(n_splits, n_groups))
    X, y = df[FEATURE_NAMES], df["selected_strategy"].to_numpy()
    oof = pd.DataFrame({"program_id": df["program_id"], "family": df["family"], "category": df["category"],
                        "true_strategy": y, "ml_strategy": "", "majority_strategy": "", "fold": -1})
    for fold, (tr, te) in enumerate(GroupKFold(n_splits=n_splits).split(X, y, groups)):
        assert not set(groups[tr]) & set(groups[te]), "family leakage between train and test"
        model = make_model().fit(X.iloc[tr], y[tr])
        oof.loc[oof.index[te], "ml_strategy"] = model.predict(X.iloc[te])
        oof.loc[oof.index[te], "majority_strategy"] = _majority(y[tr])
        oof.loc[oof.index[te], "fold"] = fold

    y_pred = oof["ml_strategy"].to_numpy()
    maj = oof["majority_strategy"].to_numpy()
    present = sorted(set(y) | set(y_pred), key=lambda s: STRATEGY_IDS.index(s) if s in STRATEGY_IDS else 99)
    metrics = {
        "evaluation": f"GroupKFold(n_splits={n_splits}) grouped by program family "
                      f"({n_groups} families, {len(df)} programs); out-of-fold predictions",
        "n_programs": int(len(df)), "n_families": int(n_groups), "n_splits": int(n_splits),
        "accuracy": float(accuracy_score(y, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, y_pred)),
        "macro_f1": float(f1_score(y, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y, y_pred, average="weighted", zero_division=0)),
        "majority_baseline_accuracy": float(accuracy_score(y, maj)),
        "fixed_s10_label_accuracy": float(np.mean(y == FIXED_STRATEGY)),
        "labels": list(STRATEGY_IDS),
        "confusion_matrix": confusion_matrix(y, y_pred, labels=list(STRATEGY_IDS)).tolist(),
        "classification_report": classification_report(y, y_pred, labels=present, output_dict=True,
                                                       zero_division=0),
        "label_distribution": {k: int(v) for k, v in sorted(Counter(y).items())},
    }
    metrics["optimization_performance"] = optimization_performance(df, oof)
    return metrics, oof


def optimization_performance(df: pd.DataFrame, oof: pd.DataFrame) -> dict:
    """Compare *cost-aware score* and *instruction-reduction %* of several selectors.

    ML and majority use held-out (out-of-fold) predictions; the oracle picks the best
    strategy per program and is an upper bound, not a deployable predictor.
    """
    idx = df.set_index("program_id")

    def mean_reduction(choice) -> tuple[float, float]:
        vals = [idx.loc[pid, f"reduction_{s}"] for pid, s in zip(oof["program_id"], choice)]
        return float(np.mean(vals)), float(np.median(vals))

    def mean_cost_score(choice) -> tuple[float, float]:
        vals = [cost_aware_score(idx.loc[pid, f"reduction_{s}"], s)
                for pid, s in zip(oof["program_id"], choice)]
        return float(np.mean(vals)), float(np.median(vals))

    selectors = {
        "oracle_best": list(oof["true_strategy"]),
        "ml_selected_heldout": list(oof["ml_strategy"]),
        "fixed_s10": [FIXED_STRATEGY] * len(oof),
        "majority_class": list(oof["majority_strategy"]),
        "fixed_s1": ["S1"] * len(oof),
    }
    out = {}
    for name, choice in selectors.items():
        mean_r, median_r = mean_reduction(choice)
        mean_s, median_s = mean_cost_score(choice)
        out[name] = {
            "mean_reduction_pct": mean_r, "median_reduction_pct": median_r,
            "mean_cost_aware_score": mean_s, "median_cost_aware_score": median_s,
        }
    ml_scores = [cost_aware_score(idx.loc[p, f"reduction_{s}"], s)
                 for p, s in zip(oof["program_id"], oof["ml_strategy"])]
    s10_scores = [cost_aware_score(idx.loc[p, f"reduction_{FIXED_STRATEGY}"], FIXED_STRATEGY)
                  for p in oof["program_id"]]
    out["ml_beats_s10_programs"] = int(sum(m > s + 1e-9 for m, s in zip(ml_scores, s10_scores)))
    out["ml_ties_s10_programs"] = int(sum(abs(m - s) <= 1e-9 for m, s in zip(ml_scores, s10_scores)))
    out["ml_loses_to_s10_programs"] = int(sum(m < s - 1e-9 for m, s in zip(ml_scores, s10_scores)))
    return out


def hyperparameter_search(df: pd.DataFrame, n_splits: int = 5) -> dict:
    """Compare multiple model configurations via GroupKFold and return results.

    Returns a dict mapping config_name -> {accuracy, macro_f1, balanced_accuracy}.
    """
    groups = df["family"].to_numpy()
    n_groups = len(set(groups))
    n_splits = max(2, min(n_splits, n_groups))
    X, y = df[FEATURE_NAMES], df["selected_strategy"].to_numpy()
    results = {}
    for name, cfg in MODEL_CONFIGS.items():
        preds = np.empty(len(y), dtype=object)
        for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
            model = cfg["cls"](**cfg["params"]).fit(X.iloc[tr], y[tr])
            preds[te] = model.predict(X.iloc[te])
        results[name] = {
            "accuracy": float(accuracy_score(y, preds)),
            "balanced_accuracy": float(balanced_accuracy_score(y, preds)),
            "macro_f1": float(f1_score(y, preds, average="macro", zero_division=0)),
        }
    return results


def feature_importance(model) -> dict[str, float]:
    imp = dict(zip(FEATURE_NAMES, (float(v) for v in model.feature_importances_)))
    return dict(sorted(imp.items(), key=lambda kv: kv[1], reverse=True))
