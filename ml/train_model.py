"""Generate data, evaluate with group-aware CV, train the final model and save artifacts.

Usage:  python -m ml.train_model            (regenerate corpus + dataset, then train)
        python -m ml.train_model --reuse-dataset
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn

from config import settings
from ml.dataset_generator import build_dataset, generate_programs, load_dataset
from ml.evaluation import RF_PARAMS, feature_importance, group_cross_validate, make_model
from ml.feature_extractor import FEATURE_NAMES
from ml.model_metadata import ModelMetadata
from utils.file_utils import atomic_write_text
from utils.logging_config import get_logger

log = get_logger(__name__)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def train_and_save(regenerate: bool = True, seed: int = settings.RANDOM_SEED) -> dict:
    """Full workflow; returns the evaluation dict that was written to disk."""
    settings.ensure_directories()
    if regenerate or not settings.DATASET_CSV.exists():
        programs = generate_programs(seed=seed)
        df = build_dataset(programs)
    else:
        df = load_dataset()

    metrics, oof = group_cross_validate(df)
    X, y = df[FEATURE_NAMES], df["selected_strategy"]
    model = make_model().fit(X, y)
    metrics["final_model_training_accuracy_in_sample"] = float(model.score(X, y))
    metrics["feature_importance"] = feature_importance(model)
    metrics["note"] = ("Reported accuracy / confusion matrix come from group-held-out cross-validation. "
                       "The in-sample training accuracy is NOT evidence of generalisation.")

    settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=settings.MODEL_DIR, suffix=".joblib")
    os.close(fd)
    joblib.dump(model, tmp)
    os.replace(tmp, settings.MODEL_FILE)

    ModelMetadata(
        model_version=settings.MODEL_VERSION, sklearn_version=sklearn.__version__,
        feature_names=list(FEATURE_NAMES), classes=[str(c) for c in model.classes_],
        trained_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        n_samples=int(len(df)), n_families=int(df["family"].nunique()), random_seed=seed,
        dataset_sha256=_sha256(settings.DATASET_CSV), hyperparameters=dict(RF_PARAMS),
    ).save()

    atomic_write_text(settings.ML_EVALUATION_JSON, json.dumps(metrics, indent=2))
    atomic_write_text(settings.OOF_PREDICTIONS_CSV, oof.to_csv(index=False))
    return metrics


def _print_summary(m: dict) -> None:
    op = m["optimization_performance"]
    print(f"Programs: {m['n_programs']}  Families: {m['n_families']}  Evaluation: {m['evaluation']}")
    print(f"Held-out accuracy: {m['accuracy']:.3f}   macro-F1: {m['macro_f1']:.3f}   "
          f"majority-baseline accuracy: {m['majority_baseline_accuracy']:.3f}")
    print(f"(in-sample training accuracy of final model: {m['final_model_training_accuracy_in_sample']:.3f} - not a generalisation measure)")
    print("Mean instruction reduction %:")
    for k in ("oracle_best", "ml_selected_heldout", "fixed_s6", "majority_class"):
        print(f"  {k:22s} {op[k]['mean_reduction_pct']:.2f}")
    print(f"ML vs S6 per program: better {op['ml_beats_s6_programs']}, equal {op['ml_ties_s6_programs']}, "
          f"worse {op['ml_loses_to_s6_programs']}")
    print("Feature importance:")
    for k, v in m["feature_importance"].items():
        print(f"  {k:28s} {v:.3f}")
    print(f"Model saved to {settings.MODEL_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the OptiWeave strategy classifier")
    parser.add_argument("--reuse-dataset", action="store_true", help="do not regenerate corpus/dataset")
    parser.add_argument("--seed", type=int, default=settings.RANDOM_SEED)
    args = parser.parse_args()
    _print_summary(train_and_save(regenerate=not args.reuse_dataset, seed=args.seed))


if __name__ == "__main__":
    main()
