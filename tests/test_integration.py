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


def test_streamlit_keeps_compiled_program_across_pages():
    """Source compiled in the editor must remain the active program on later pages.

    Streamlit deletes widget keys when those widgets are not rendered. The source
    text used to live in a widget key, so leaving Source Editor reset the program
    to mixed.ow and later pages asked to compile again / showed S10 of mixed.ow.
    """
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    arithmetic = (settings.EXAMPLES_DIR / "arithmetic.ow").read_text(encoding="utf-8")
    mixed = (settings.EXAMPLES_DIR / "mixed.ow").read_text(encoding="utf-8")
    at = AppTest.from_file(str(settings.PROJECT_ROOT / "app.py"), default_timeout=90).run()
    assert not at.exception

    at.sidebar.radio[0].set_value("Source Editor").run()
    at.selectbox[0].set_value("arithmetic.ow").run()
    assert at.session_state["program_source"] == arithmetic
    assert at.session_state["program_name"] == "arithmetic.ow"
    at.button[0].click().run()
    assert not at.exception
    fe = at.session_state["frontend"]
    assert fe is not None and fe.ok
    assert fe.source == arithmetic
    opt = at.session_state["opt_result"]
    assert opt is not None
    assert at.session_state["opt_source"] == arithmetic

    for page in ["Compiler Explorer", "Optimization Lab", "Generated Code"]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page
        assert at.session_state["program_source"] == arithmetic, page
        assert at.session_state["program_source"] != mixed, page
        assert at.session_state["frontend"].source == arithmetic, page
        infos = [str(item.value) for item in at.info]
        assert not any("Compile a program" in msg or "Compile a valid program" in msg for msg in infos), (
            f"{page} lost the compiled program: {infos}"
        )

    at.sidebar.radio[0].set_value("Generated Code").run()
    radios = [str(item.value) for item in at.radio]
    assert any("Optimization Lab / ML" in value for value in radios)
    assert at.session_state["opt_result"].strategy_id == opt.strategy_id

    at.sidebar.radio[0].set_value("Source Editor").run()
    assert at.session_state["program_source"] == arithmetic
    assert at.selectbox[0].value == "arithmetic.ow"

    sid = opt.strategy_id
    at.sidebar.radio[0].set_value("Benchmark Comparison").run()
    assert not at.exception
    captions = " ".join(str(c.value) for c in at.caption)
    assert "arithmetic.ow" in captions
    metric_labels = [getattr(m, "label", "") for m in at.metric]
    metric_values = [str(getattr(m, "value", "")) for m in at.metric]
    assert "Selected strategy" in metric_labels
    assert sid in metric_values
    assert "Fixed S10 (corpus mean)" in metric_labels

    at.sidebar.radio[0].set_value("ML Analytics").run()
    assert not at.exception
    captions = " ".join(str(c.value) for c in at.caption)
    assert "arithmetic.ow" in captions
    metric_labels = [getattr(m, "label", "") for m in at.metric]
    metric_values = [str(getattr(m, "value", "")) for m in at.metric]
    assert "Predicted strategy" in metric_labels
    assert sid in metric_values
    assert "Held-out accuracy" in metric_labels

    at.sidebar.radio[0].set_value("Documentation / About").run()
    assert not at.exception
    captions = " ".join(str(c.value) for c in at.caption)
    infos = " ".join(str(i.value) for i in at.info)
    assert "arithmetic.ow" in captions
    assert sid in infos
    assert "S10" in infos and "baseline" in infos.lower()
