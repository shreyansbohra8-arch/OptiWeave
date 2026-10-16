import pytest

from benchmarking.benchmark_runner import benchmark_program, records_to_dataframe, run_corpus
from benchmarking.equivalence import check_equivalence, run_ir
from benchmarking.metrics import median_or_none, summarize
from compiler.code_generator import RunResult
from ml.dataset_generator import BenchmarkProgram
from ml.predictor import StrategyPredictor
from tests.conftest import compile_ir, requires_gcc
from pathlib import Path


@pytest.fixture(scope="module")
def predictor(trained):
    return StrategyPredictor.load(trained["model_path"], trained["meta_path"])


def test_interpreter_matches_expected_output():
    assert run_ir(compile_ir("int i = 0; while (i < 3) { print(i * 2); i = i + 1; }")).output == ["0", "2", "4"]


def test_interpreter_step_limit_and_runtime_error():
    assert run_ir(compile_ir("int i = 0; while (true) { i = i + 1; }"), max_steps=1000).limit_exceeded
    assert "division by zero" in run_ir(compile_ir("int z = 0; print(1 / z);")).error


def test_equivalence_detects_a_wrong_optimisation():
    a = compile_ir("int x = 1; print(x);")
    b = compile_ir("int x = 2; print(x);")
    assert not check_equivalence(a, b).equivalent


def test_median_helpers():
    assert median_or_none([3.0, 1.0, 2.0]) == 2.0 and median_or_none([]) is None
    r = RunResult(True, times_s=[0.3, 0.1, 0.2, 0.4])
    assert r.median_time_s == pytest.approx(0.25)


def test_benchmark_program_without_gcc(predictor, trained):
    prog = trained["programs"][0]
    rec = benchmark_program(prog, predictor, use_gcc=False)
    assert rec.status == "ok" and set(rec.variants) == {"unoptimized", "fixed_s6", "ml_selected"}
    assert rec.variants["unoptimized"].reduction_pct == 0.0
    assert rec.ir_equivalent and rec.ml_strategy.startswith("S")


@requires_gcc
def test_benchmark_program_with_gcc_and_summary(predictor, trained):
    progs = trained["programs"][:4]
    recs = run_corpus(progs, predictor, None, use_gcc=True, repeats=2)
    assert all(r.status == "ok" and r.gcc_outputs_match for r in recs)
    s = summarize(recs)
    assert s["gcc_compiled_programs"] == 4 and not s["gcc_output_mismatches"]
    assert s["mean_reduction_pct"]["fixed_s6"] >= s["mean_reduction_pct"]["ml_selected"] - 1e-9
    assert len(records_to_dataframe(recs)) == 4


def test_benchmark_reports_compile_failures(predictor):
    bad = BenchmarkProgram("bad", "mixed", "bad", Path("bad.ow"), "int x = ;")
    rec = benchmark_program(bad, predictor, use_gcc=False)
    assert rec.status == "error" and "parser" in rec.error
    assert summarize([rec])["programs_failed"][0]["program_id"] == "bad"


def test_zero_instruction_program_does_not_divide_by_zero(predictor):
    prog = BenchmarkProgram("empty", "mixed", "empty", Path("e.ow"), "// nothing\n")
    rec = benchmark_program(prog, predictor, use_gcc=False)
    assert rec.status == "ok" and rec.variants["fixed_s6"].reduction_pct == 0.0
