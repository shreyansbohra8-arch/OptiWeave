"""Inference: load the trained Random Forest and predict an optimisation strategy."""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from config import settings
from ml.feature_extractor import FEATURE_NAMES
from ml.model_metadata import ModelMetadata
from optimizer.strategies import STRATEGY_IDS
from utils.exceptions import IncompatibleModelError, ModelNotFoundError


@dataclass
class Prediction:
    strategy_id: str
    confidence: float
    probabilities: dict


def _check_sklearn_version(metadata: ModelMetadata) -> None:
    """Warn if the current scikit-learn version differs from what the model was trained with."""
    current = sklearn.__version__
    trained = metadata.sklearn_version
    if current != trained:
        current_major_minor = ".".join(current.split(".")[:2])
        trained_major_minor = ".".join(trained.split(".")[:2])
        if current_major_minor != trained_major_minor:
            warnings.warn(
                f"scikit-learn version mismatch: model was trained with {trained}, "
                f"but current version is {current}. The model may fail to load or "
                f"produce different results. Retrain with: python -m ml.train_model",
                UserWarning,
                stacklevel=3,
            )


class StrategyPredictor:
    def __init__(self, model, metadata: ModelMetadata) -> None:
        self.model = model
        self.metadata = metadata

    @classmethod
    def load(cls, model_path: Path = settings.MODEL_FILE,
             metadata_path: Path = settings.MODEL_METADATA_FILE) -> "StrategyPredictor":
        if not Path(model_path).exists():
            raise ModelNotFoundError(
                f"No trained model at {model_path}. Train it with: python -m ml.train_model")
        metadata = ModelMetadata.load(metadata_path)
        metadata.validate()
        _check_sklearn_version(metadata)
        try:
            model = joblib.load(model_path)
        except Exception as exc:  # corrupt / incompatible pickle
            raise IncompatibleModelError(
                f"Could not load model ({exc}). Retrain with: python -m ml.train_model") from exc
        if list(getattr(model, "classes_", [])) != list(metadata.classes):
            raise IncompatibleModelError("Model classes differ from metadata. Retrain the model.")
        if not set(metadata.classes) <= set(STRATEGY_IDS):
            raise IncompatibleModelError("Model predicts unknown strategies. Retrain the model.")
        return cls(model, metadata)

    def predict(self, features: dict) -> Prediction:
        row = pd.DataFrame([[features[n] for n in FEATURE_NAMES]], columns=FEATURE_NAMES)
        probs = self.model.predict_proba(row)[0]
        proba = {str(c): float(p) for c, p in zip(self.model.classes_, probs)}
        best = max(proba, key=lambda k: (proba[k], -int(k[1:])))
        return Prediction(best, proba[best], proba)


def model_status() -> tuple[bool, str]:
    """(available, message) for display in the UI."""
    try:
        meta = StrategyPredictor.load().metadata
        return True, f"Model v{meta.model_version} trained {meta.trained_at} on {meta.n_samples} programs"
    except (ModelNotFoundError, IncompatibleModelError) as exc:
        return False, str(exc)
