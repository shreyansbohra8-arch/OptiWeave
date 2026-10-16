"""Command-line driver: python -m compiler.cli examples/mixed.ow [--strategy auto|S1..S6] [--gcc]"""
from __future__ import annotations

import argparse
import sys

from benchmarking.equivalence import check_equivalence
from compiler.code_generator import compile_and_run, find_gcc, generate_c
from compiler.pipeline import compile_front_end
from config import settings
from ml.feature_extractor import extract_features
from optimizer.optimization_pipeline import describe_passes, run_strategy
from optimizer.strategies import STRATEGY_IDS
from utils.exceptions import IncompatibleModelError, ModelNotFoundError
from utils.file_utils import read_source, write_inside
from utils.validation import safe_stem, validate_ow_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OptiWeave command-line compiler")
    ap.add_argument("file", help="path to a .ow source file")
    ap.add_argument("--strategy", default="auto", choices=["auto", *STRATEGY_IDS])
    ap.add_argument("--gcc", action="store_true", help="compile and run the generated C with GCC -O0")
    ap.add_argument("--save", action="store_true", help="save generated C under outputs/generated_c")
    args = ap.parse_args(argv)

    try:
        path = validate_ow_path(args.file)
        source = read_source(path)
    except Exception as exc:  # noqa: BLE001 - user-facing message
        print(f"error: {exc}", file=sys.stderr)
        return 2
    fe = compile_front_end(source)
    if not fe.ok:
        print(f"Compilation failed at the {fe.failed_stage} stage:", file=sys.stderr)
        for e in fe.errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    print(f"== Original IR ({fe.ir.instruction_count} instructions, {len(fe.cfg.blocks)} blocks, "
          f"{fe.cfg.edge_count} edges) ==")
    print(fe.ir.to_text())
    features = extract_features(fe.ir, fe.cfg)
    print("\n== Features ==")
    for k, v in features.items():
        print(f"  {k:28s} {v}")
    strategy = args.strategy
    if strategy == "auto":
        try:
            from ml.predictor import StrategyPredictor
            pred = StrategyPredictor.load().predict(features)
        except (ModelNotFoundError, IncompatibleModelError) as exc:
            print(f"\nerror: {exc}", file=sys.stderr)
            return 3
        strategy = pred.strategy_id
        print(f"\nML-selected strategy: {strategy} (confidence {pred.confidence:.2f})")
    res = run_strategy(fe.ir, strategy)
    print(f"Strategy {strategy}: {describe_passes(strategy)}")
    print(f"Passes that changed the IR: {', '.join(res.passes_applied) or 'none'}")
    print(f"\n== Optimized IR ==\n{res.optimized.to_text()}")
    print(f"\nInstructions: {res.original_count} -> {res.optimized_count} "
          f"({res.reduction_pct:.2f}% reduction)")
    eq = check_equivalence(fe.ir, res.optimized)
    print(f"Equivalence check: {'passed' if eq.equivalent else 'FAILED'} ({eq.detail})")
    c_src = generate_c(res.optimized)
    if args.save:
        out = write_inside(settings.GENERATED_C_DIR, f"{safe_stem(path.stem)}_{strategy}.c", c_src)
        print(f"C code written to {out}")
    if args.gcc:
        if find_gcc() is None:
            print("GCC not found; skipping compilation.")
        else:
            comp, run = compile_and_run(c_src)
            if not comp.ok:
                print("GCC failed:\n" + (comp.stderr or comp.message))
                return 4
            print("GCC compilation OK. Program output:")
            print(run.stdout if run.ok else run.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
