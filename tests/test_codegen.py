import tempfile

from benchmarking.equivalence import compare_outputs, run_ir
from compiler.code_generator import compile_and_run, compile_c, find_gcc, generate_c, run_executable
from optimizer.optimization_pipeline import run_strategy
from tests.conftest import compile_ir, requires_gcc


def test_generated_c_structure():
    c = generate_c(compile_ir("int a = 2; float f = a * 1.5; bool b = f > 2.0; while (a < 5) { a = a + 1; } print(a); print(f); print(b);"))
    assert "int main(void)" in c and "long long a" in c and "double f" in c and "bool b" in c
    assert "goto L" in c and "if (" in c and "ow_print_bool" in c and '"%.6f\\n"' in c and "return 0;" in c


def test_division_uses_checked_helpers():
    c = generate_c(compile_ir("int a = 7; int z = 2; int q = a / z; int r = a % z; float f = 1.5 / 2.0;"))
    assert "ow_div_i" in c and "ow_mod_i" in c and "ow_div_f" in c


@requires_gcc
def test_gcc_output_matches_interpreter_for_all_strategies():
    src = ("int i = 0; int s = 0; float f = 0.5; bool flag = false; "
           "while (i < 10) { if (i % 3 == 0 && i > 2) { s = s + i * 2; flag = true; } else { s = s - 1; } f = f * 1.5 + i; i = i + 1; } "
           "print(s); print(f); print(flag); print(-7 / 2); print(-7 % 3);")
    ir = compile_ir(src)
    expected = run_ir(ir).output
    for sid in ["S1", "S4", "S6"]:
        comp, run = compile_and_run(generate_c(run_strategy(ir, sid).optimized))
        assert comp.ok, comp.stderr
        assert compare_outputs(run.stdout, "\n".join(expected))


@requires_gcc
def test_runtime_division_by_zero_is_reported():
    ir = compile_ir("int z = 0; int x = 5 / z; print(x);")
    comp, run = compile_and_run(generate_c(ir))
    assert comp.ok and not run.ok and "division by zero" in run.stderr


@requires_gcc
def test_compile_error_is_captured():
    with tempfile.TemporaryDirectory() as tmp:
        res = compile_c("int main( { return 0; }", tmp, "bad")
    assert not res.ok and res.stderr


@requires_gcc
def test_run_timeout_is_enforced():
    with tempfile.TemporaryDirectory() as tmp:
        comp = compile_c("int main(void){ for(;;){} return 0; }", tmp, "spin")
        assert comp.ok
        res = run_executable(comp.exe_path, timeout=1)
    assert res.timed_out and not res.ok


def test_missing_gcc_is_reported(monkeypatch):
    monkeypatch.setenv("PATH", "")
    monkeypatch.delenv("OPTIWEAVE_GCC", raising=False)
    assert find_gcc() is None
    res = compile_c("int main(void){return 0;}", "unused_dir_does_not_matter")
    assert not res.ok and "GCC was not found" in res.message
