from compiler.ir import Assign, BinOp, CondJump, Const, Jump, Label, Print, UnOp, Var, evaluate_binop
from tests.conftest import compile_ir


def test_spec_example_three_address_code():
    ir = compile_ir("int a = 1; int b = 2; int x = a + b * 2;")
    text = [str(i) for i in ir.instructions]
    assert text[-3:] == ["t1 = b * 2", "t2 = a + t1", "x = t2"]


def test_temporaries_do_not_collide_with_user_names():
    ir = compile_ir("int t1 = 1; int y = t1 + 2;")
    assert any(isinstance(i, BinOp) and i.dst != "t1" for i in ir.instructions)
    assert "t1" not in ir.temps


def test_instruction_kinds_for_control_flow():
    ir = compile_ir("int i = 0; while (i < 3) { if (i == 1) { print(i); } else { i = i + 0; } i = i + 1; }")
    kinds = {type(i) for i in ir.instructions}
    assert {Assign, BinOp, CondJump, Jump, Label, Print} <= kinds


def test_branch_targets_exist():
    ir = compile_ir("int i = 0; while (i < 3) { i = i + 1; } if (i > 1) { print(i); }")
    labels = {i.name for i in ir.instructions if isinstance(i, Label)}
    for ins in ir.instructions:
        if isinstance(ins, Jump):
            assert ins.target in labels
        if isinstance(ins, CondJump):
            assert ins.true_target in labels and ins.false_target in labels


def test_unary_and_default_values():
    ir = compile_ir("int a; float f; bool b; int c = -a;")
    assert Assign("a", Const(0)) in ir.instructions
    assert Assign("f", Const(0.0)) in ir.instructions
    assert Assign("b", Const(False)) in ir.instructions
    assert any(isinstance(i, UnOp) for i in ir.instructions)


def test_int_literal_widened_for_float_variable():
    ir = compile_ir("float f = 3;")
    assert ir.instructions[0] == Assign("f", Const(3.0))


def test_short_circuit_generates_branches():
    ir = compile_ir("int a = 0; bool b = a != 0 && 10 / a > 1;")
    assert any(isinstance(i, CondJump) for i in ir.instructions)


def test_const_equality_distinguishes_types():
    assert Const(1) != Const(1.0) and Const(1) != Const(True) and Const(2) == Const(2)


def test_instruction_count_excludes_labels():
    ir = compile_ir("int i = 0; while (i < 2) { i = i + 1; }")
    assert ir.instruction_count == len([i for i in ir.instructions if not isinstance(i, Label)])


def test_evaluation_semantics():
    assert evaluate_binop("/", -7, 2) == -3  # truncation toward zero like C
    assert evaluate_binop("%", -7, 2) == -1
    assert evaluate_binop("/", 7, 2.0) == 3.5
    assert evaluate_binop("+", 2**63 - 1, 1) == -(2**63)  # 64-bit wrap
