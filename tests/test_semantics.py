import pytest

from compiler.lexer import tokenize
from compiler.parser import parse
from compiler.semantic_analyzer import analyze, check
from utils.exceptions import SemanticErrors


def A(src):
    return analyze(parse(tokenize(src)))


def errors(src):
    return [str(e) for e in A(src).errors]


def test_valid_program():
    assert A("int a = 1; float f = a + 1.5; bool b = a < 3; if (b) { print(f); }").ok


def test_symbol_table_contents():
    res = A("int a = 1; { float b = 2.0; }")
    assert [(s.name, s.type) for s in res.symbols.all_symbols()] == [("a", "int"), ("b", "float")]


def test_undefined_variable_use_and_assign():
    assert any("undeclared" in e for e in errors("print(x);"))
    assert any("undeclared" in e for e in errors("y = 3;"))


def test_duplicate_declaration():
    assert any("Duplicate" in e for e in errors("int a = 1; int a = 2;"))


def test_shadowing_and_reuse_in_sibling_blocks_rejected():
    assert any("Duplicate" in e for e in errors("int a = 1; { int a = 2; }"))
    assert any("Duplicate" in e for e in errors("{ int a = 1; } { int a = 2; }"))


def test_block_scope_visibility():
    assert any("undeclared" in e for e in errors("{ int a = 1; } print(a);"))


def test_type_mismatches():
    assert any("Cannot assign" in e for e in errors("int a = 1.5;"))
    assert any("Cannot assign" in e for e in errors("bool b = 1;"))
    assert any("Cannot assign" in e for e in errors("int a = true;"))
    assert A("float f = 1;").ok  # widening allowed


def test_invalid_conditions():
    assert any("must be bool" in e for e in errors("int a = 1; if (a) { }"))
    assert any("must be bool" in e for e in errors("while (1 + 2) { }"))


def test_invalid_operations():
    assert errors("bool b = true + 1;")
    assert errors("float f = 1.5; int m = f % 2;")
    assert errors("bool b = !3;")
    assert errors("bool b = true < false;")
    assert errors("bool b = 1 && 2;")
    assert errors("int a = 1; bool b = a == true;")


def test_division_by_literal_zero():
    assert any("Division by zero" in e for e in errors("int a = 5 / 0;"))
    assert any("Modulo by zero" in e for e in errors("int a = 5 % 0;"))


def test_numeric_promotion_types():
    res = A("int i = 1; float f = i * 2.0;")
    assert res.ok


def test_check_raises():
    with pytest.raises(SemanticErrors):
        check(parse(tokenize("print(q);")))


def test_multiple_errors_collected():
    assert len(errors("print(a); print(b);")) == 2
