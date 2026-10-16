import pytest

from compiler.lexer import tokenize
from compiler.tokens import TokenType as T
from utils.exceptions import LexerError


def types(src):
    return [t.type for t in tokenize(src)]


def test_all_token_kinds():
    src = "int float bool if else while print true false x 12 3.5 + - * / % < > <= >= == != && || ! = ( ) { } ;"
    got = types(src)
    expected = [T.KW_INT, T.KW_FLOAT, T.KW_BOOL, T.KW_IF, T.KW_ELSE, T.KW_WHILE, T.KW_PRINT, T.BOOL_LIT, T.BOOL_LIT,
                T.IDENT, T.INT_LIT, T.FLOAT_LIT, T.PLUS, T.MINUS, T.STAR, T.SLASH, T.PERCENT, T.LT, T.GT, T.LE, T.GE,
                T.EQ, T.NE, T.AND, T.OR, T.NOT, T.ASSIGN, T.LPAREN, T.RPAREN, T.LBRACE, T.RBRACE, T.SEMI, T.EOF]
    assert got == expected


def test_keyword_vs_identifier():
    toks = tokenize("integer int whiley while")
    assert [t.type for t in toks[:4]] == [T.IDENT, T.KW_INT, T.IDENT, T.KW_WHILE]


def test_float_and_int_literals():
    toks = tokenize("3.14 42 0.5")
    assert toks[0].value == 3.14 and toks[1].value == 42 and toks[2].value == 0.5
    assert toks[0].type is T.FLOAT_LIT and toks[1].type is T.INT_LIT


def test_malformed_float_rejected():
    with pytest.raises(LexerError):
        tokenize("1.")
    with pytest.raises(LexerError):
        tokenize("12abc")


def test_multichar_operators_not_split():
    assert types("a<=b==c!=d>=e")[1::2][:4] == [T.LE, T.EQ, T.NE, T.GE]
    assert types("a<b") [1] is T.LT


def test_comments_and_whitespace_skipped():
    src = "int x; // line comment\n/* block\n comment */ x = 1;"
    got = types(src)
    assert T.SLASH not in got and got.count(T.SEMI) == 2


def test_unterminated_block_comment():
    with pytest.raises(LexerError):
        tokenize("/* never closed")


def test_invalid_character_reports_location():
    with pytest.raises(LexerError) as exc:
        tokenize("int a;\n  @")
    assert exc.value.line == 2 and exc.value.column == 3


def test_single_ampersand_hint():
    with pytest.raises(LexerError, match="&&"):
        tokenize("a & b")


def test_line_and_column_tracking():
    toks = tokenize("int x;\n  y = 2;")
    y = [t for t in toks if t.lexeme == "y"][0]
    assert (y.line, y.column) == (2, 3)
