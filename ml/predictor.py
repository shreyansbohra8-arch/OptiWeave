"""Inference: load the trained Random Forest and predict an optimisation strategy."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

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
