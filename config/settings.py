"""Central configuration for OptiWeave (paths, seeds, limits, toolchain settings)."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
BENCHMARK_DIR = DATA_DIR / "benchmarks"
DATASET_DIR = DATA_DIR / "datasets"
RESULTS_DIR = DATA_DIR / "results"
MODEL_DIR = PROJECT_ROOT / "models"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
GENERATED_C_DIR = OUTPUT_DIR / "generated_c"
GENERATED_IR_DIR = OUTPUT_DIR / "generated_ir"
REPORTS_DIR = OUTPUT_DIR / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"

DATASET_CSV = DATASET_DIR / "optiweave_dataset.csv"
STRATEGY_RESULTS_CSV = DATASET_DIR / "strategy_results.csv"
MODEL_FILE = MODEL_DIR / "optiweave_rf.joblib"
MODEL_METADATA_FILE = MODEL_DIR / "model_metadata.json"
ML_EVALUATION_JSON = RESULTS_DIR / "ml_evaluation.json"
OOF_PREDICTIONS_CSV = RESULTS_DIR / "oof_predictions.csv"
BENCHMARK_RESULTS_CSV = RESULTS_DIR / "benchmark_results.csv"
BENCHMARK_SUMMARY_JSON = RESULTS_DIR / "benchmark_summary.json"

RANDOM_SEED = 42
MODEL_VERSION = "1.0.0"

# Source / execution limits
MAX_SOURCE_BYTES = 100_000
MAX_INT_LITERAL = 2**63 - 1
MAX_OPT_ITERATIONS = 10
INTERPRETER_MAX_STEPS = 2_000_000

# GCC integration (optimisation intentionally disabled; -fwrapv gives defined
# 64-bit wrap-around so that C output matches the IR interpreter).
GCC_FLAGS = ["-O0", "-std=c11", "-fwrapv"]
COMPILE_TIMEOUT_S = 30
RUN_TIMEOUT_S = 20
TIMING_REPEATS = 5
# Medians below this threshold are dominated by process start-up noise.
MIN_RELIABLE_RUNTIME_S = 0.010

# Optional environment overrides (see .env.example)
GCC_ENV_VAR = "OPTIWEAVE_GCC"
LOG_LEVEL = os.environ.get("OPTIWEAVE_LOG_LEVEL", "WARNING").upper()


def ensure_directories() -> None:
    """Create every output directory the application writes into."""
    for path in (BENCHMARK_DIR, DATASET_DIR, RESULTS_DIR, MODEL_DIR,
                 GENERATED_C_DIR, GENERATED_IR_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
