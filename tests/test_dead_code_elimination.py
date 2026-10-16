from benchmarking.equivalence import check_equivalence, run_ir
from compiler.ir import Jump
from optimizer.constant_folding import run as cf
from optimizer.dead_code_elimination import run as dce
from tests.conftest import compile_ir


def lines(ir):
    return [str(i) for i in ir.instructions]


def test_overwritten_assignment_removed():
    out, n = dce(compile_ir("int x = 10; x = 20; print(x);"))
    assert "x = 10" not in lines(out) and "x = 20" in lines(out) and n >= 1


def test_unused_computation_removed_including_temps():
    out, _ = dce(compile_ir("int a = 1; int b = 2; int unused = a * b + 3; print(a);"))
    assert not any("unused" in l or "t1" in l for l in lines(out))


def test_print_is_never_removed():
    ir = compile_ir("int x = 1; print(x); print(x);")
    out, _ = dce(ir)
    assert sum(1 for l in lines(out) if l.startswith("print")) == 2


def test_possible_fault_is_preserved():
    ir = compile_ir("int z = 0; int unused = 5 / z;")
    out, _ = dce(ir)
    assert any("/" in l for l in lines(out))
    assert run_ir(out).error is not None


def test_loop_carried_variable_kept():
    ir = compile_ir("int i = 0; int s = 0; while (i < 4) { s = s + i; i = i + 1; } print(s);")
    out, _ = dce(ir)
    assert check_equivalence(ir, out).equivalent
    assert any("s = " in l for l in lines(out))


def test_unreachable_code_and_redundant_jump_removed():
    ir, _ = cf(compile_ir("if (true) { print(1); } else { print(2); }"))
    out, _ = dce(ir)
    assert "print 2" not in lines(out)
    assert not any(isinstance(i, Jump) for i in out.instructions)
    assert run_ir(out).output == ["1"]


def test_control_flow_behaviour_preserved():
    ir = compile_ir("int i = 0; int dead = 0; while (i < 5) { dead = i * 3; if (i % 2 == 0) { print(i); } i = i + 1; }")
    out, _ = dce(ir)
    assert check_equivalence(ir, out).equivalent
    assert out.instruction_count < ir.instruction_count


def test_self_referential_dead_accumulator_is_kept_documented_limitation():
    # Plain liveness cannot prove `dead = dead + i` useless (it "uses" itself); faint-variable
    # analysis would. The pass must stay correct, so it keeps the accumulator.
    ir = compile_ir("int i = 0; int dead = 0; while (i < 5) { dead = dead + i; i = i + 1; } print(i);")
    out, _ = dce(ir)
    assert check_equivalence(ir, out).equivalent
    assert any("dead = " in str(i) for i in out.instructions)
