"""Model metadata: feature order, class mapping and version, stored beside the model."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from config import settings
from ml.feature_extractor import FEATURE_NAMES
from utils.exceptions import IncompatibleModelError, ModelNotFoundError
from utils.file_utils import atomic_write_text


@dataclass
class ModelMetadata:
    model_version: str
    sklearn_version: str
    feature_names: list
    classes: list
    trained_at: str
    n_samples: int
    n_families: int
    random_seed: int
    dataset_sha256: str
    hyperparameters: dict = field(default_factory=dict)

    def save(self, path: Path = settings.MODEL_METADATA_FILE) -> None:
        atomic_write_text(path, json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path = settings.MODEL_METADATA_FILE) -> "ModelMetadata":
        if not Path(path).exists():
            raise ModelNotFoundError(
                f"Model metadata not found at {path}. Train the model first: python -m ml.train_model")
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls(**data)
        except (json.JSONDecodeError, TypeError) as exc:
            raise IncompatibleModelError(f"Model metadata is corrupt ({exc}). Retrain with: "
                                         "python -m ml.train_model") from exc

    def validate(self) -> None:
        if self.model_version != settings.MODEL_VERSION:
            raise IncompatibleModelError(
                f"Model version {self.model_version} != expected {settings.MODEL_VERSION}. "
                "Retrain with: python -m ml.train_model")
        if list(self.feature_names) != FEATURE_NAMES:
            raise IncompatibleModelError(
                "Model was trained with a different feature set/order. "
                "Retrain with: python -m ml.train_model")
