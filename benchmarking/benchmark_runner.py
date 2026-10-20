"""Benchmark: unoptimized vs fixed S10 vs ML-selected strategy.

Usage: python -m benchmarking.benchmark_runner [--repeats 5] [--no-gcc] [--final-model]
"""
from __future__ import annotations

import argparse
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from benchmarking.equivalence import check_equivalence, compare_outputs
from benchmarking.metrics import summarize
from compiler.code_generator import compile_c, find_gcc, generate_c, run_executable
from compiler.ir import IRProgram
from compiler.pipeline import compile_front_end
from config import settings
from ml.dataset_generator import BenchmarkProgram, load_programs
from ml.feature_extractor import extract_features
from ml.predictor import StrategyPredictor
from optimizer.optimization_pipeline import instruction_reduction_pct, run_strategy
from optimizer.strategies import FIXED_STRATEGY
from utils.exceptions import OptiWeaveError
from utils.logging_config import get_logger

log = get_logger(__name__)
VARIANTS = ("unoptimized", "fixed_s10", "ml_selected")


@dataclass
class VariantResult:
    strategy: str
    original_count: int
    optimized_count: int
    reduction_pct: float
    compile_ok: bool = False
    compile_error: str = ""
    compile_time_s: float | None = None
    run_ok: bool = False
    output: str = ""
    median_time_s: float | None = None
    timing_reliable: bool = False


@dataclass
class BenchmarkRecord:
    program_id: str
    category: str
    family: str
    ml_strategy: str = ""
    ml_confidence: float | None = None
    prediction_source: str = ""
    variants: dict = field(default_factory=dict)
    ir_equivalent: bool = True
    equivalence_checked: bool = False
    equivalence_detail: str = ""
    gcc_outputs_match: bool | None = None
    status: str = "ok"
    error: str = ""


def _measure(ir: IRProgram, strategy_label: str, original_count: int, use_gcc: bool,
             repeats: int, workdir: Path, stem: str) -> VariantResult:
    v = VariantResult(strategy_label, original_count, ir.instruction_count,
                      instruction_reduction_pct(original_count, ir.instruction_count))
    if not use_gcc:
        v.compile_error = "GCC not used"
        return v
    comp = compile_c(generate_c(ir), workdir, stem)
    v.compile_ok, v.compile_time_s = comp.ok, comp.compile_time_s
    if not comp.ok:
        v.compile_error = (comp.stderr or comp.message)[:500]
        return v
    run = run_executable(comp.exe_path, repeats)
    v.run_ok, v.output = run.ok, run.stdout
    if not run.ok:
        v.compile_error = f"run failed: {run.stderr[:300]}"
    v.median_time_s = run.median_time_s
    v.timing_reliable = bool(run.ok and v.median_time_s and v.median_time_s >= settings.MIN_RELIABLE_RUNTIME_S)
    return v


def benchmark_program(program: BenchmarkProgram, predictor: StrategyPredictor,
                      predicted_strategy: str | None = None, prediction_source: str = "final model",
                      use_gcc: bool = True, repeats: int = settings.TIMING_REPEATS) -> BenchmarkRecord:
    rec = BenchmarkRecord(program.program_id, program.category, program.family)
    fe = compile_front_end(program.source)
    if not fe.ok:
        rec.status, rec.error = "error", f"[{fe.failed_stage}] " + "; ".join(fe.errors)
        return rec
    feats = extract_features(fe.ir, fe.cfg)
    if predicted_strategy is None:
        pred = predictor.predict(feats)
        rec.ml_strategy, rec.ml_confidence = pred.strategy_id, pred.confidence
    else:
        rec.ml_strategy = predicted_strategy
        rec.ml_confidence = predictor.predict(feats).probabilities.get(predicted_strategy)
    rec.prediction_source = prediction_source

    n0 = fe.ir.instruction_count
    s10 = run_strategy(fe.ir, FIXED_STRATEGY)
    ml = run_strategy(fe.ir, rec.ml_strategy)
    irs = {"unoptimized": ("none", fe.ir), "fixed_s10": (FIXED_STRATEGY, s10.optimized),
           "ml_selected": (rec.ml_strategy, ml.optimized)}

    eq_details = []
    for name in ("fixed_s10", "ml_selected"):
        eq = check_equivalence(fe.ir, irs[name][1])
        rec.equivalence_checked = rec.equivalence_checked or eq.checked
        if eq.checked and not eq.equivalent:
            rec.ir_equivalent = False
        eq_details.append(f"{name}: {eq.detail}")
    rec.equivalence_detail = "; ".join(eq_details)

    gcc_ok = use_gcc and find_gcc() is not None
    with tempfile.TemporaryDirectory(prefix="optiweave_bench_") as tmp:
        for name, (label, ir) in irs.items():
            rec.variants[name] = _measure(ir, label, n0, gcc_ok, repeats, Path(tmp), f"{program.program_id}_{name}")
    if gcc_ok and all(v.run_ok for v in rec.variants.values()):
        base = rec.variants["unoptimized"].output
        rec.gcc_outputs_match = all(compare_outputs(base, v.output) for v in rec.variants.values())
    return rec


def run_corpus(programs: list[BenchmarkProgram], predictor: StrategyPredictor,
               oof_map: dict[str, str] | None, use_gcc: bool = True,
               repeats: int = settings.TIMING_REPEATS) -> list[BenchmarkRecord]:
    records = []
    for p in programs:
        try:
            if oof_map and p.program_id in oof_map:
                rec = benchmark_program(p, predictor, oof_map[p.program_id],
                                        "group-held-out cross-validation prediction", use_gcc, repeats)
            else:
                rec = benchmark_program(p, predictor, None,
                                        "final model (program NOT in training corpus)"
                                        if p.category == "timing-workload" else
                                        "final model (in-sample: program was in the training data)",
                                        use_gcc, repeats)
        except OptiWeaveError as exc:
            rec = BenchmarkRecord(p.program_id, p.category, p.family, status="error", error=str(exc))
        records.append(rec)
    return records


def records_to_dataframe(records: list[BenchmarkRecord]) -> pd.DataFrame:
    rows = []
    for r in records:
        row = {"program_id": r.program_id, "category": r.category, "family": r.family, "status": r.status,
               "error": r.error, "ml_strategy": r.ml_strategy, "ml_confidence": r.ml_confidence,
               "prediction_source": r.prediction_source, "ir_equivalent": r.ir_equivalent,
               "equivalence_checked": r.equivalence_checked, "gcc_outputs_match": r.gcc_outputs_match}
        for name, v in r.variants.items():
            row.update({f"{name}_strategy": v.strategy, f"{name}_instructions": v.optimized_count,
                        f"{name}_reduction_pct": round(v.reduction_pct, 4),
                        f"{name}_gcc_compiled": v.compile_ok, f"{name}_run_ok": v.run_ok,
                        f"{name}_median_time_s": v.median_time_s,
                        f"{name}_timing_reliable": v.timing_reliable})
        if r.variants:
            row["original_instructions"] = r.variants["unoptimized"].original_count
        rows.append(row)
    return pd.DataFrame(rows)


def load_timing_workloads() -> list[BenchmarkProgram]:
    """Heavy programs from examples/ used to obtain measurable run times."""
    out = []
    timing_files = [
        "heavy_loop.ow",
        "nested_heavy.ow",
        "iterative_power.ow",
        "large_accumulator.ow",
        "redundant_heavy.ow",
        "strength_heavy.ow",
    ]
    for filename in timing_files:
        path = settings.EXAMPLES_DIR / filename
        if path.exists():
            stem = path.stem
            out.append(BenchmarkProgram(f"timing_{stem}", "timing-workload",
                                        f"timing_{stem}", path,
                                        path.read_text(encoding="utf-8")))
    return out


def main() -> None:
    from benchmarking.report_generator import write_reports
    parser = argparse.ArgumentParser(description="Run the OptiWeave benchmark")
    parser.add_argument("--repeats", type=int, default=settings.TIMING_REPEATS)
    parser.add_argument("--no-gcc", action="store_true")
    parser.add_argument("--final-model", action="store_true",
                        help="use the final (in-sample) model instead of held-out CV predictions")
    parser.add_argument("--limit", type=int, default=0, help="only benchmark the first N programs")
    args = parser.parse_args()

    settings.ensure_directories()
    predictor = StrategyPredictor.load()
    programs = load_programs()
    if not programs:
        raise SystemExit("No benchmark programs found. Run: python -m ml.train_model")
    if args.limit:
        programs = programs[:args.limit]
    oof_map = None
    if not args.final_model and settings.OOF_PREDICTIONS_CSV.exists():
        oof = pd.read_csv(settings.OOF_PREDICTIONS_CSV)
        oof_map = dict(zip(oof["program_id"], oof["ml_strategy"]))
    programs = programs + load_timing_workloads()
    if find_gcc() is None and not args.no_gcc:
        print("WARNING: GCC not found - only IR instruction-count metrics will be produced.")
    records = run_corpus(programs, predictor, oof_map, use_gcc=not args.no_gcc, repeats=args.repeats)
    summary = write_reports(records)
    print(f"Benchmarked {summary['programs_ok']}/{summary['programs_total']} programs")
    print("Mean reduction %:", {k: round(v, 2) for k, v in summary["mean_reduction_pct"].items()})
    print("ML vs S10:", summary["ml_vs_s10"])
    print("Timing:", summary["timing"]["programs_with_reliable_timing"], "programs with reliable timing")
    print(f"Reports written to {settings.RESULTS_DIR} and {settings.REPORTS_DIR}")


if __name__ == "__main__":
    main()
