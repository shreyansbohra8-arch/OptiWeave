"""Shared pytest fixtures and helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.code_generator import find_gcc  # noqa: E402
from compiler.pipeline import compile_or_raise  # noqa: E402

requires_gcc = pytest.mark.skipif(find_gcc() is None, reason="GCC is not installed / not on PATH")


def compile_ir(source: str):
    """Compile source through the front end and return the IRProgram."""
    return compile_or_raise(source).ir


@pytest.fixture(scope="session")
def trained(tmp_path_factory):
    """A model trained into a temporary directory (real artifacts are never touched)."""
    import joblib

    from ml.dataset_generator import build_dataset, generate_programs
    from ml.evaluation import group_cross_validate, make_model
    from ml.feature_extractor import FEATURE_NAMES
    from ml.model_metadata import ModelMetadata
    from config import settings
    import sklearn

    tmp = tmp_path_factory.mktemp("ml")
    programs = generate_programs(tmp / "bench")
    df = build_dataset(programs, tmp / "dataset.csv", tmp / "results.csv")
    metrics, oof = group_cross_validate(df)
    model = make_model().fit(df[FEATURE_NAMES], df["selected_strategy"])
    model_path, meta_path = tmp / "model.joblib", tmp / "meta.json"
    joblib.dump(model, model_path)
    ModelMetadata(settings.MODEL_VERSION, sklearn.__version__, list(FEATURE_NAMES),
                  [str(c) for c in model.classes_], "test", len(df), df["family"].nunique(), 42,
                  "x", {}).save(meta_path)
    return {"tmp": tmp, "programs": programs, "df": df, "metrics": metrics, "oof": oof,
            "model_path": model_path, "meta_path": meta_path}
