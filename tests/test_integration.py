from pathlib import Path

import pytest

from benchmarking.benchmark_runner import benchmark_program
from benchmarking.equivalence import check_equivalence, run_ir
from compiler.code_generator import compile_and_run, generate_c
from compiler.pipeline import compile_front_end
from config import settings
from ml.dataset_generator import BenchmarkProgram
from ml.feature_extractor import FEATURE_NAMES, extract_features
from ml.predictor import StrategyPredictor
from optimizer.optimization_pipeline import run_strategy
from tests.conftest import requires_gcc

EXAMPLES = sorted(settings.EXAMPLES_DIR.glob("*.ow"))
VALID = [p for p in EXAMPLES if p.name != "invalid_program.ow"]


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_every_example_runs_the_front_end_and_optimizer(path):
    fe = compile_front_end(path.read_text())
    assert fe.ok, fe.errors
    for sid in ["S1", "S6"]:
        assert check_equivalence(fe.ir, run_strategy(fe.ir, sid).optimized, max_steps=300_000).equivalent


@requires_gcc
def test_full_pipeline_source_to_benchmark(trained):
    predictor = StrategyPredictor.load(trained["model_path"], trained["meta_path"])
    src = (settings.EXAMPLES_DIR / "mixed.ow").read_text()
    fe = compile_front_end(src)
    assert fe.ok and fe.cfg.blocks
    feats = extract_features(fe.ir, fe.cfg)
    assert list(feats) == FEATURE_NAMES
    pred = predictor.predict(feats)
    res = run_strategy(fe.ir, pred.strategy_id)
    assert res.optimized_count <= res.original_count
    c_src = generate_c(res.optimized)
    comp, run = compile_and_run(c_src)
    assert comp.ok and run.ok
    assert run.stdout.split() == run_ir(fe.ir).output
    rec = benchmark_program(BenchmarkProgram("mixed", "mixed", "mixed", Path("m.ow"), src), predictor, repeats=2)
    assert rec.status == "ok" and rec.gcc_outputs_match


@pytest.mark.parametrize("src, stage", [
    ("int a = 5; bool f = a + 1;", "semantic"),
    ("int a = ;", "parser"),
    ("int a = 3 $ 4;", "lexer"),
    ("print(zzz);", "semantic"),
])
def test_invalid_programs_are_rejected_before_codegen(src, stage):
    fe = compile_front_end(src)
    assert not fe.ok and fe.failed_stage == stage
    assert fe.ir is None and fe.cfg is None  # nothing reaches IR / optimisation / codegen


def test_invalid_example_file_rejected():
    fe = compile_front_end((settings.EXAMPLES_DIR / "invalid_program.ow").read_text())
    assert not fe.ok and len(fe.errors) == 2


def test_oversized_and_nul_input_rejected():
    assert compile_front_end("\x00").failed_stage == "input"
    assert compile_front_end("x" * (settings.MAX_SOURCE_BYTES + 1)).failed_stage == "input"


def test_streamlit_app_smoke():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(settings.PROJECT_ROOT / "app.py"), default_timeout=90).run()
    assert not at.exception
    for page in ["Source Editor", "Compiler Explorer", "Optimization Lab", "Generated Code",
                 "Benchmark Comparison", "ML Analytics", "Documentation / About"]:
        at.sidebar.radio[0].set_value(page).run()
        if page == "Source Editor":
            at.button[0].click().run()
        assert not at.exception, page
