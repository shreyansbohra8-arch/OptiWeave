from benchmarking.equivalence import check_equivalence
from compiler.ir import BinOp
from optimizer.common_subexpression import run as cse
from tests.conftest import compile_ir


def adds(ir, op="+"):
    return [i for i in ir.instructions if isinstance(i, BinOp) and i.op == op]


def test_repeated_expression_reused():
    ir = compile_ir("int b = 1; int c = 2; int a = b + c; int d = b + c; print(a + d);")
    out, n = cse(ir)
    assert n == 1
    assert len([i for i in adds(out) if str(i.left) == "b" and str(i.right) == "c"]) == 1
    assert out.instruction_count == ir.instruction_count - 1
    assert check_equivalence(ir, out).equivalent


def test_operand_modification_invalidates():
    ir = compile_ir("int b = 1; int c = 2; int a = b + c; b = 5; int d = b + c; print(a); print(d);")
    out, n = cse(ir)
    assert n == 0 and len(adds(out)) == len(adds(ir))
    assert check_equivalence(ir, out).equivalent


def test_commutative_operands_matched():
    ir = compile_ir("int b = 3; int c = 4; int a = b * c; int d = c * b; print(a + d);")
    out, n = cse(ir)
    assert n == 1 and check_equivalence(ir, out).equivalent


def test_non_commutative_not_matched():
    ir = compile_ir("int b = 3; int c = 4; int a = b - c; int d = c - b; print(a); print(d);")
    _, n = cse(ir)
    assert n == 0


def test_holder_redefined_before_use_is_rematerialised():
    ir = compile_ir("int b = 1; int c = 2; int a = b + c; int d = b + c; a = 100; print(d); print(a);")
    out, _ = cse(ir)
    assert check_equivalence(ir, out).equivalent


def test_does_not_cross_basic_blocks():
    ir = compile_ir("int b = 1; int c = 2; int a = b + c; if (a > 0) { int d = b + c; print(d); }")
    _, n = cse(ir)
    assert n == 0


def test_loop_body_redundancy():
    ir = compile_ir("int x = 1; int i = 0; int o = 0; while (i < 4) { int p = x + i; int q = x + i; o = o + p * q; i = i + 1; } print(o);")
    out, n = cse(ir)
    assert n >= 1 and check_equivalence(ir, out).equivalent
