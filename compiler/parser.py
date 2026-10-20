"""Recursive-descent parser for OptiWeave (grammar in docs/LANGUAGE_GRAMMAR.md).

Supports **panic-mode error recovery**: when a parse error is encountered,
the parser records the error, advances to the next synchronisation point
(typically a semicolon or closing brace), and continues parsing.  This
allows reporting multiple errors in a single pass.
"""
from __future__ import annotations

from compiler import ast_nodes as ast
from compiler.tokens import TYPE_KEYWORDS, Token, TokenType as T
from config import settings
from utils.exceptions import ParseError


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.i = 0
        self.errors: list[ParseError] = []

    # -- helpers -------------------------------------------------------------
    @property
    def cur(self) -> Token:
        return self.tokens[self.i]

    def _check(self, *types: T) -> bool:
        return self.cur.type in types

    def _advance(self) -> Token:
        tok = self.cur
        if tok.type is not T.EOF:
            self.i += 1
        return tok

    def _expect(self, ttype: T, what: str) -> Token:
        if self.cur.type is not ttype:
            found = "end of input" if self.cur.type is T.EOF else repr(self.cur.lexeme)
            raise ParseError(f"Expected {what}, found {found}", self.cur.line, self.cur.column)
        return self._advance()

    def _synchronize(self) -> None:
        """Panic-mode recovery: advance past the next semicolon or closing brace."""
        while not self._check(T.EOF):
            if self._check(T.SEMI):
                self._advance()
                return
            if self._check(T.RBRACE):
                self._advance()
                return
            # Statement-starting tokens are also sync points (don't consume them)
            if self.cur.type in (*TYPE_KEYWORDS, T.KW_IF, T.KW_WHILE, T.KW_PRINT):
                return
            self._advance()

    # -- program / statements --------------------------------------------------
    def parse(self) -> ast.Program:
        prog = ast.Program(line=1, column=1)
        while not self._check(T.EOF):
            try:
                prog.statements.append(self._statement())
            except ParseError as err:
                self.errors.append(err)
                self._synchronize()
        # If errors were collected, raise the first one but attach all errors
        if self.errors:
            first = self.errors[0]
            first.all_errors = self.errors  # type: ignore[attr-defined]
            raise first
        return prog

    def _statement(self) -> ast.Stmt:
        tok = self.cur
        if tok.type in TYPE_KEYWORDS:
            return self._declaration()
        if tok.type is T.IDENT:
            return self._assignment()
        if tok.type is T.KW_IF:
            return self._if()
        if tok.type is T.KW_WHILE:
            return self._while()
        if tok.type is T.KW_PRINT:
            return self._print()
        if tok.type is T.LBRACE:
            return self._block()
        if tok.type is T.RBRACE:
            raise ParseError("Unmatched '}'", tok.line, tok.column)
        raise ParseError(f"Unexpected token {tok.lexeme!r}; expected a statement",
                         tok.line, tok.column)

    def _declaration(self) -> ast.VarDecl:
        tok = self._advance()
        name = self._expect(T.IDENT, "variable name")
        init = None
        if self._check(T.ASSIGN):
            self._advance()
            init = self._expr()
        self._expect(T.SEMI, "';'")
        return ast.VarDecl(tok.line, tok.column, TYPE_KEYWORDS[tok.type], name.lexeme, init)

    def _assignment(self) -> ast.Assign:
        name = self._advance()
        self._expect(T.ASSIGN, "'=' after variable name")
        value = self._expr()
        self._expect(T.SEMI, "';'")
        return ast.Assign(name.line, name.column, name.lexeme, value)

    def _print(self) -> ast.Print:
        tok = self._advance()
        self._expect(T.LPAREN, "'(' after print")
        value = self._expr()
        self._expect(T.RPAREN, "')'")
        self._expect(T.SEMI, "';'")
        return ast.Print(tok.line, tok.column, value)

    def _block(self) -> ast.Block:
        lbrace = self._expect(T.LBRACE, "'{'")
        block = ast.Block(lbrace.line, lbrace.column)
        while not self._check(T.RBRACE):
            if self._check(T.EOF):
                raise ParseError("Missing '}' before end of input", lbrace.line, lbrace.column)
            try:
                block.statements.append(self._statement())
            except ParseError as err:
                self.errors.append(err)
                self._synchronize()
        self._advance()
        return block

    def _if(self) -> ast.If:
        tok = self._advance()
        self._expect(T.LPAREN, "'(' after if")
        cond = self._expr()
        self._expect(T.RPAREN, "')'")
        then_block = self._block()
        else_block = None
        if self._check(T.KW_ELSE):
            else_tok = self._advance()
            if self._check(T.KW_IF):  # else-if chain: desugar into nested if
                nested = self._if()
                else_block = ast.Block(else_tok.line, else_tok.column, [nested])
            else:
                else_block = self._block()
        return ast.If(tok.line, tok.column, cond, then_block, else_block)

    def _while(self) -> ast.While:
        tok = self._advance()
        self._expect(T.LPAREN, "'(' after while")
        cond = self._expr()
        self._expect(T.RPAREN, "')'")
        body = self._block()
        return ast.While(tok.line, tok.column, cond, body)

    # -- expressions (lowest to highest precedence) ----------------------------
    def _binary_level(self, next_level, ops: dict) -> ast.Expr:
        left = next_level()
        while self.cur.type in ops:
            op_tok = self._advance()
            right = next_level()
            left = ast.Binary(op_tok.line, op_tok.column, op=op_tok.lexeme, left=left, right=right)
        return left

    def _expr(self) -> ast.Expr:
        return self._or()

    def _or(self) -> ast.Expr:
        return self._binary_level(self._and, {T.OR: "||"})

    def _and(self) -> ast.Expr:
        return self._binary_level(self._equality, {T.AND: "&&"})

    def _equality(self) -> ast.Expr:
        return self._binary_level(self._relational, {T.EQ: "==", T.NE: "!="})

    def _relational(self) -> ast.Expr:
        return self._binary_level(self._additive, {T.LT: "<", T.GT: ">", T.LE: "<=", T.GE: ">="})

    def _additive(self) -> ast.Expr:
        return self._binary_level(self._term, {T.PLUS: "+", T.MINUS: "-"})

    def _term(self) -> ast.Expr:
        return self._binary_level(self._unary, {T.STAR: "*", T.SLASH: "/", T.PERCENT: "%"})

    def _unary(self) -> ast.Expr:
        if self._check(T.MINUS, T.NOT):
            tok = self._advance()
            return ast.Unary(tok.line, tok.column, op=tok.lexeme, operand=self._unary())
        return self._primary()

    def _primary(self) -> ast.Expr:
        tok = self.cur
        if tok.type is T.INT_LIT:
            self._advance()
            if tok.value > settings.MAX_INT_LITERAL:
                raise ParseError("Integer literal too large for a 64-bit int", tok.line, tok.column)
            return ast.Literal(tok.line, tok.column, value=tok.value, literal_type="int")
        if tok.type is T.FLOAT_LIT:
            self._advance()
            return ast.Literal(tok.line, tok.column, value=tok.value, literal_type="float")
        if tok.type is T.BOOL_LIT:
            self._advance()
            return ast.Literal(tok.line, tok.column, value=tok.value, literal_type="bool")
        if tok.type is T.IDENT:
            self._advance()
            return ast.Variable(tok.line, tok.column, name=tok.lexeme)
        if tok.type is T.LPAREN:
            self._advance()
            inner = self._expr()
            self._expect(T.RPAREN, "')'")
            return inner
        found = "end of input" if tok.type is T.EOF else repr(tok.lexeme)
        raise ParseError(f"Expected an expression, found {found}", tok.line, tok.column)


def parse(tokens: list[Token]) -> ast.Program:
    """Convenience wrapper."""
    return Parser(tokens).parse()
