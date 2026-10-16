import pytest

from compiler import ast_nodes as ast
from compiler.lexer import tokenize
from compiler.parser import parse
from utils.exceptions import ParseError


def P(src):
    return parse(tokenize(src))


def expr(src):
    return P(f"int x = {src};").statements[0].init


def test_precedence_mul_over_add():
    e = expr("1 + 2 * 3")
    assert e.op == "+" and e.right.op == "*"


def test_left_associativity():
    e = expr("10 - 4 - 3")
    assert e.op == "-" and e.left.op == "-" and e.right.value == 3


def test_parentheses_override():
    e = expr("(1 + 2) * 3")
    assert e.op == "*" and e.left.op == "+"


def test_logical_precedence_and_over_or():
    e = P("bool b = true || false && true;").statements[0].init
    assert e.op == "||" and e.right.op == "&&"


def test_relational_over_logical():
    e = P("bool b = 1 < 2 && 3 > 2;").statements[0].init
    assert e.op == "&&" and e.left.op == "<"


def test_unary_negative_literal():
    e = expr("-5")
    assert isinstance(e, ast.Unary) and e.op == "-" and e.operand.value == 5


def test_declaration_assignment_print():
    prog = P("int a = 1; int b; a = 2; print(a);")
    kinds = [type(s).__name__ for s in prog.statements]
    assert kinds == ["VarDecl", "VarDecl", "Assign", "Print"]
    assert prog.statements[1].init is None


def test_if_else_and_else_if():
    prog = P("if (true) { print(1); } else if (false) { print(2); } else { print(3); }")
    s = prog.statements[0]
    assert isinstance(s, ast.If) and isinstance(s.else_block.statements[0], ast.If)


def test_while_and_nesting():
    prog = P("int i = 0; while (i < 3) { if (i == 1) { print(i); } i = i + 1; }")
    w = prog.statements[1]
    assert isinstance(w, ast.While) and isinstance(w.body.statements[0], ast.If)


@pytest.mark.parametrize("src", [
    "int x = ;", "int x = 1", "x = 1 +;", "if (true) print(1);", "while true { }",
    "{ print(1);", "print(1);}", "int = 3;", "print 1;", "else { }",
])
def test_syntax_errors(src):
    with pytest.raises(ParseError):
        P(src)


def test_syntax_error_location():
    with pytest.raises(ParseError) as exc:
        P("int a = 1;\nint b = ;")
    assert exc.value.line == 2


def test_int_literal_too_large():
    with pytest.raises(ParseError):
        P("int x = 99999999999999999999;")
