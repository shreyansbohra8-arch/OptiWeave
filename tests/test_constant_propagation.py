from benchmarking.equivalence import check_equivalence
from compiler.ir import Assign, Const
from optimizer.constant_folding import run as cf
from optimizer.constant_propagation import run as cp
from tests.conftest import compile_ir


def lines(ir):
    return [str(i) for i in ir.instructions]


def test_straight_line_propagation():
    out, _ = cp(compile_ir("int x = 10; int y = x + 5; print(y);"))
    assert "t1 = 10 + 5" in lines(out)


def test_reassignment_invalidates():
    out, _ = cp(compile_ir("int x = 1; x = 2; print(x);"))
    assert "print 2" in lines(out)


def test_non_constant_not_propagated():
    out, _ = cp(compile_ir("int x = 1; int i = 0; while (i < 3) { x = x + 1; i = i + 1; } print(x);"))
    assert "print x" in lines(out)


def test_merge_with_conflicting_values_not_propagated():
    ir = compile_ir("int i = 0; int x = 1; while (i < 4) { if (i % 2 == 0) { x = 2; } else { x = 3; } i = i + 1; } print(x);")
    out, _ = cp(ir)
    assert "print x" in lines(out)  # x is 2 on one path and 3 on the other
    assert check_equivalence(ir, out).equivalent


def test_merge_with_equal_values_propagated():
    src = "int c = 0; int x = 0; if (c < 5) { x = 7; } else { x = 7; } print(x);"
    # c is a known constant so the branch is not decided by CP alone; x is 7 on both paths
    out, _ = cp(compile_ir(src))
    assert "print 7" in lines(out)


def test_loop_invariant_constant_propagated_into_loop():
    out, _ = cp(compile_ir("int k = 4; int i = 0; while (i < k) { i = i + 1; } print(i);"))
    assert any("i < 4" in l for l in lines(out))


def test_float_coercion_keeps_type():
    ir = compile_ir("float f = 5; float g = f / 2; print(g);")
    out, _ = cp(ir)
    assert check_equivalence(ir, out).equivalent
    assert Assign("f", Const(5.0)) in out.instructions


def test_behaviour_preserved_on_loop_program():
    ir = compile_ir("int a = 3; int s = 0; int i = 0; while (i < 5) { s = s + a * i; i = i + 1; } print(s);")
    out, _ = cp(ir)
    assert check_equivalence(ir, out).equivalent
