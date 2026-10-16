import json

import joblib
import pandas as pd
import pytest

from config import settings
from ml.dataset_generator import choose_best_strategy, generate_programs, load_dataset
from ml.evaluation import group_cross_validate
from ml.feature_extractor import FEATURE_NAMES
from ml.model_metadata import ModelMetadata
from ml.predictor import StrategyPredictor
from optimizer.strategies import STRATEGY_IDS
from utils.exceptions import DatasetError, IncompatibleModelError, ModelNotFoundError


def test_corpus_size_categories_and_uniqueness(trained):
    progs = trained["programs"]
    assert 55 <= len(progs) <= 65
    assert len({p.source for p in progs}) == len(progs)
    assert len({p.program_id for p in progs}) == len(progs)
    assert len({p.category for p in progs}) == 6
    assert all(p.path.exists() for p in progs)


def test_generation_is_deterministic(tmp_path):
    a = generate_programs(tmp_path / "a", write=False)
    b = generate_programs(tmp_path / "b", write=False)
    assert [p.source for p in a] == [p.source for p in b]


def test_dataset_columns_and_labels(trained):
    df = trained["df"]
    for col in FEATURE_NAMES + ["program_id", "category", "selected_strategy", "original_instructions",
                                "optimized_instructions", "instruction_reduction_pct"]:
        assert col in df.columns
    assert set(df["selected_strategy"]) <= set(STRATEGY_IDS)
    # labels come from the optimiser: the chosen strategy's reduction is the maximum
    for _, row in df.iterrows():
        best = max(row[f"reduction_{s}"] for s in STRATEGY_IDS)
        assert row["instruction_reduction_pct"] == pytest.approx(best)
    # labels are not a function of category alone
    assert df.groupby("category")["selected_strategy"].nunique().max() > 1


def test_results_table_has_all_strategies(trained):
    long = pd.read_csv(trained["tmp"] / "results.csv")
    assert set(long["strategy"]) == set(STRATEGY_IDS)
    assert long["equivalent"].all()


def test_group_aware_evaluation_has_no_family_leakage(trained):
    oof, df = trained["oof"], trained["df"]
    assert (oof["fold"] >= 0).all()
    fam_folds = oof.groupby("family")["fold"].nunique()
    assert (fam_folds == 1).all(), "a family appears in more than one test fold"
    m = trained["metrics"]
    assert 0.0 <= m["accuracy"] <= 1.0 and len(m["confusion_matrix"]) == 6
    assert "ml_selected_heldout" in m["optimization_performance"]
    assert m["optimization_performance"]["oracle_best"]["mean_reduction_pct"] >= \
        m["optimization_performance"]["ml_selected_heldout"]["mean_reduction_pct"] - 1e-9


def test_model_load_and_predict(trained):
    p = StrategyPredictor.load(trained["model_path"], trained["meta_path"])
    feats = dict(zip(FEATURE_NAMES, [20, 8, 1, 1, 6, 0, 1, 7, 5, 7]))
    pred = p.predict(feats)
    assert pred.strategy_id in STRATEGY_IDS
    assert abs(sum(pred.probabilities.values()) - 1.0) < 1e-9
    assert 0 < pred.confidence <= 1


def test_missing_model_gives_helpful_error(tmp_path):
    with pytest.raises(ModelNotFoundError, match="python -m ml.train_model"):
        StrategyPredictor.load(tmp_path / "none.joblib", tmp_path / "none.json")


def test_incompatible_metadata_detected(trained, tmp_path):
    meta = ModelMetadata.load(trained["meta_path"])
    meta.feature_names = list(reversed(meta.feature_names))
    bad = tmp_path / "bad.json"
    meta.save(bad)
    with pytest.raises(IncompatibleModelError):
        StrategyPredictor.load(trained["model_path"], bad)
    meta.feature_names = list(FEATURE_NAMES)
    meta.model_version = "0.0.0"
    meta.save(bad)
    with pytest.raises(IncompatibleModelError):
        StrategyPredictor.load(trained["model_path"], bad)


def test_corrupt_model_file(trained, tmp_path):
    corrupt = tmp_path / "corrupt.joblib"
    corrupt.write_text("not a model")
    with pytest.raises(IncompatibleModelError):
        StrategyPredictor.load(corrupt, trained["meta_path"])


def test_missing_dataset_error(tmp_path):
    with pytest.raises(DatasetError):
        load_dataset(tmp_path / "missing.csv")


def test_model_is_reproducible(trained):
    df = trained["df"]
    m2, _ = group_cross_validate(df)
    assert m2["accuracy"] == trained["metrics"]["accuracy"]
