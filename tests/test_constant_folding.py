from benchmarking.equivalence import check_equivalence
from compiler.ir import Assign, Const, Jump
from optimizer.constant_folding import run
from tests.conftest import compile_ir


def lines(ir):
    return [str(i) for i in ir.instructions]


def test_folds_integer_expression():
    out, n = run(compile_ir("int x = 10 + 20;"))
    assert "t1 = 30" in lines(out) and n == 1


def test_respects_int_division_and_float():
    out, _ = run(compile_ir("int a = 7 / 2; float b = 7 / 2.0; int c = 7 % 4;"))
    text = lines(out)
    assert "t1 = 3" in text and "t2 = 3.5" in text and "t3 = 3" in text


def test_negative_literal_folded():
    out, _ = run(compile_ir("int x = -5;"))
    assert Assign("t1", Const(-5)) in out.instructions


def test_relational_and_boolean_folding():
    out, _ = run(compile_ir("bool b = 3 < 5; bool c = !true;"))
    assert Assign("t1", Const(True)) in out.instructions and Assign("t2", Const(False)) in out.instructions


def test_division_by_zero_not_folded():
    ir = compile_ir("int z = 0; int x = 1 / z;")  # divisor is a variable, so analysis passes
    out, _ = run(ir)
    assert any(str(i) == "t1 = 1 / z" for i in out.instructions)


def test_constant_branch_becomes_jump():
    out, _ = run(compile_ir("if (1 < 2) { print(1); } else { print(2); }"))
    assert any(isinstance(i, Jump) for i in out.instructions)


def test_folding_keeps_behaviour():
    ir = compile_ir("int x = 2 * 3 + 4 * 5; float f = 1 + 2.5; print(x); print(f);")
    out, _ = run(ir)
    assert check_equivalence(ir, out).equivalent


def test_idempotent():
    ir = compile_ir("int x = 1 + 2;")
    once, _ = run(ir)
    twice, n = run(once)
    assert once == twice and n == 0
