"""Benchmark-corpus and labelled-dataset generation.

Labels come from *running the optimiser*: every program is optimised with all ten
strategies, and the best strategy is chosen by a **cost-aware score** that balances
instruction-count reduction against the compile-time cost of the pipeline.  Ties go
to the pipeline with fewer passes, then to the lower strategy number.  Category is
never used to choose a label.
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from benchmarking.equivalence import check_equivalence, run_ir
from compiler.pipeline import compile_front_end
from config import settings
from ml.feature_extractor import FEATURE_NAMES, extract_features
from ml.program_templates import CATEGORIES, VARIANTS_PER_FAMILY
from optimizer.optimization_pipeline import instruction_reduction_pct, run_strategy
from optimizer.strategies import STRATEGIES, STRATEGY_IDS, cost_aware_score
from utils.exceptions import DatasetError
from utils.file_utils import atomic_write_text
from utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class BenchmarkProgram:
    program_id: str
    category: str
    family: str
    path: Path
    source: str


def choose_best_strategy(optimized_counts: dict[str, int],
                         original_count: int) -> str:
    """Best strategy by cost-aware score: reduction% minus cost penalty.

    Ties are broken by fewer passes, then lower strategy number.
    """
    def _key(sid: str):
        reduction = instruction_reduction_pct(original_count, optimized_counts[sid])
        score = cost_aware_score(reduction, sid)
        return (score, -len(STRATEGIES[sid].passes), -STRATEGIES[sid].number)
    return max(optimized_counts, key=_key)


def generate_programs(out_dir: Path = settings.BENCHMARK_DIR,
                      seed: int = settings.RANDOM_SEED, write: bool = True) -> list[BenchmarkProgram]:
    """Generate the benchmark corpus deterministically."""
    programs: list[BenchmarkProgram] = []
    seen_sources: set[str] = set()
    for category, (short, families) in CATEGORIES.items():
        for fi, fam in enumerate(families, start=1):
            family_id = f"{short}_f{fi}"
            for v in range(1, VARIANTS_PER_FAMILY + 1):
                pid = f"{family_id}_v{v}"
                rng = random.Random(f"{seed}:{pid}")
                src = fam(rng)
                attempts = 0
                while src in seen_sources and attempts < 20:  # guarantee distinct programs
                    src, attempts = fam(rng), attempts + 1
                if src in seen_sources:
                    raise DatasetError(f"Could not generate a distinct program for {pid}")
                seen_sources.add(src)
                header = f"// {pid} | category: {category} | family: {family_id}\n"
                path = Path(out_dir) / f"{pid}.ow"
                programs.append(BenchmarkProgram(pid, category, family_id, path, header + src))
    if write:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        for p in programs:
            atomic_write_text(p.path, p.source)
    return programs


def load_programs(directory: Path = settings.BENCHMARK_DIR) -> list[BenchmarkProgram]:
    """Load previously generated corpus files (metadata parsed from the header comment)."""
    programs = []
    for path in sorted(Path(directory).glob("*.ow")):
        text = path.read_text(encoding="utf-8")
        first = text.splitlines()[0] if text else ""
        pid = path.stem
        category, family = "unknown", pid.rsplit("_v", 1)[0]
        if first.startswith("//") and "|" in first:
            parts = [x.strip() for x in first[2:].split("|")]
            category = parts[1].replace("category:", "").strip()
            family = parts[2].replace("family:", "").strip()
        programs.append(BenchmarkProgram(pid, category, family, path, text))
    return programs


def evaluate_program(program: BenchmarkProgram) -> tuple[dict, list[dict]]:
    """Run all ten strategies on a program; returns (dataset row, long-format result rows)."""
    fe = compile_front_end(program.source)
    if not fe.ok:
        raise DatasetError(f"{program.program_id} failed to compile: {fe.errors}")
    base = run_ir(fe.ir)
    if not base.ok:
        raise DatasetError(f"{program.program_id} fails at run time: {base.error}")
    feats = extract_features(fe.ir, fe.cfg)
    orig = fe.ir.instruction_count
    counts, long_rows = {}, []
    for sid in STRATEGY_IDS:
        res = run_strategy(fe.ir, sid)
        eq = check_equivalence(fe.ir, res.optimized)
        if not eq.equivalent:
            raise DatasetError(f"{program.program_id}/{sid} changed behaviour: {eq.detail}")
        counts[sid] = res.optimized_count
        reduction = round(instruction_reduction_pct(orig, res.optimized_count), 4)
        long_rows.append({
            "program_id": program.program_id, "strategy": sid,
            "passes": STRATEGIES[sid].label, "original_instructions": orig,
            "optimized_instructions": res.optimized_count,
            "instruction_reduction_pct": reduction,
            "cost_aware_score": round(cost_aware_score(reduction, sid), 4),
            "equivalent": eq.equivalent,
        })
    best = choose_best_strategy(counts, orig)
    row = {"program_id": program.program_id, "category": program.category, "family": program.family}
    row.update(feats)
    row.update({f"reduction_{sid}": round(instruction_reduction_pct(orig, counts[sid]), 4)
                for sid in STRATEGY_IDS})
    row.update({f"score_{sid}": round(cost_aware_score(
                    instruction_reduction_pct(orig, counts[sid]), sid), 4)
                for sid in STRATEGY_IDS})
    row.update({
        "selected_strategy": best,
        "original_instructions": orig,
        "optimized_instructions": counts[best],
        "instruction_reduction_pct": round(instruction_reduction_pct(orig, counts[best]), 4),
    })
    return row, long_rows


def build_dataset(programs: list[BenchmarkProgram],
                  dataset_csv: Path = settings.DATASET_CSV,
                  results_csv: Path = settings.STRATEGY_RESULTS_CSV) -> pd.DataFrame:
    rows, long_rows = [], []
    for p in programs:
        row, lr = evaluate_program(p)
        rows.append(row)
        long_rows.extend(lr)
    df = pd.DataFrame(rows)
    atomic_write_text(dataset_csv, df.to_csv(index=False))
    atomic_write_text(results_csv, pd.DataFrame(long_rows).to_csv(index=False))
    return df


def load_dataset(path: Path = settings.DATASET_CSV) -> pd.DataFrame:
    """Load and validate the dataset CSV."""
    if not Path(path).exists():
        raise DatasetError(f"Dataset not found at {path}. Run: python -m ml.train_model")
    df = pd.read_csv(path)
    required = {"program_id", "category", "family", "selected_strategy", *FEATURE_NAMES}
    missing = required - set(df.columns)
    if missing:
        raise DatasetError(f"Dataset is missing columns: {sorted(missing)}")
    if df["selected_strategy"].isin(STRATEGY_IDS).sum() != len(df):
        raise DatasetError("Dataset contains labels outside S1..S10")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the OptiWeave benchmark corpus and dataset")
    parser.add_argument("--seed", type=int, default=settings.RANDOM_SEED)
    args = parser.parse_args()
    settings.ensure_directories()
    programs = generate_programs(seed=args.seed)
    df = build_dataset(programs)
    print(f"Generated {len(programs)} programs -> {settings.DATASET_CSV}")
    print(df["selected_strategy"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
