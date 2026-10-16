"""Semantic analysis: scopes, declaration checks and type checking.

Type rules (see docs/LANGUAGE_GRAMMAR.md):
  * ``int`` and ``float`` are numeric. ``int op float`` promotes to ``float``.
  * ``%`` requires two ``int`` operands.
  * Relational ``< > <= >=`` need numeric operands; ``== !=`` accept two numeric
    operands or two ``bool`` operands. All comparisons yield ``bool``.
  * ``&& || !`` need ``bool`` operands. Conditions must be ``bool``.
  * Assignment: ``int -> float`` widening is allowed; ``float -> int`` is rejected.
  * Every variable name may be declared only once in the whole program.
  * Division/modulo by a literal zero is a compile-time error.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from compiler import ast_nodes as ast
from compiler.symbol_table import SymbolTable
from utils.exceptions import SemanticError, SemanticErrors

NUMERIC = ("int", "float")
ERR = "error"


@dataclass
class SemanticResult:
    errors: list[SemanticError] = field(default_factory=list)
    symbols: SymbolTable = field(default_factory=SymbolTable)

    @property
    def ok(self) -> bool:
        return not self.errors


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.table = SymbolTable()
        self.errors: list[SemanticError] = []

    def _err(self, node: ast.Node, message: str) -> None:
        self.errors.append(SemanticError(message, node.line, node.column))

    # -- entry points ------------------------------------------------------------
    def analyze(self, program: ast.Program) -> SemanticResult:
        for stmt in program.statements:
            self._stmt(stmt)
        return SemanticResult(self.errors, self.table)

    # -- statements ---------------------------------------------------------------
    def _stmt(self, s: ast.Stmt) -> None:
        if isinstance(s, ast.VarDecl):
            init_t = self._expr(s.init) if s.init is not None else None
            prev = self.table.declared_before(s.name)
            if prev is not None:
                self._err(s, f"Duplicate declaration of '{s.name}' "
                             f"(first declared at line {prev.line}); names must be unique")
            else:
                self.table.declare(s.name, s.var_type, s.line, s.column)
            if init_t is not None:
                self._check_assignable(s, s.var_type, init_t, s.name)
        elif isinstance(s, ast.Assign):
            sym = self.table.lookup(s.name)
            vt = self._expr(s.value)
            if sym is None:
                self._err(s, f"Assignment to undeclared variable '{s.name}'")
            else:
                self._check_assignable(s, sym.type, vt, s.name)
        elif isinstance(s, ast.Print):
            self._expr(s.value)
        elif isinstance(s, ast.Block):
            self.table.enter_scope()
            for inner in s.statements:
                self._stmt(inner)
            self.table.exit_scope()
        elif isinstance(s, ast.If):
            self._condition(s.condition, "if")
            self._stmt(s.then_block)
            if s.else_block is not None:
                self._stmt(s.else_block)
        elif isinstance(s, ast.While):
            self._condition(s.condition, "while")
            self._stmt(s.body)

    def _condition(self, expr: ast.Expr, kw: str) -> None:
        t = self._expr(expr)
        if t not in ("bool", ERR):
            self._err(expr, f"Condition of '{kw}' must be bool, found {t}")

    def _check_assignable(self, node: ast.Node, target: str, source: str, name: str) -> None:
        if source == ERR or target == source:
            return
        if target == "float" and source == "int":
            return
        self._err(node, f"Cannot assign {source} to {target} variable '{name}'")

    # -- expressions ----------------------------------------------------------------
    def _expr(self, e: ast.Expr) -> str:
        t = self._expr_inner(e)
        e.type = t
        return t

    def _expr_inner(self, e: ast.Expr) -> str:
        if isinstance(e, ast.Literal):
            return e.literal_type
        if isinstance(e, ast.Variable):
            sym = self.table.lookup(e.name)
            if sym is None:
                self._err(e, f"Use of undeclared variable '{e.name}'")
                return ERR
            return sym.type
        if isinstance(e, ast.Unary):
            t = self._expr(e.operand)
            if t == ERR:
                return ERR
            if e.op == "-":
                if t in NUMERIC:
                    return t
                self._err(e, f"Unary '-' requires a numeric operand, found {t}")
                return ERR
            if t == "bool":
                return "bool"
            self._err(e, f"'!' requires a bool operand, found {t}")
            return ERR
        if isinstance(e, ast.Binary):
            return self._binary(e)
        self._err(e, "Unsupported expression")
        return ERR

    def _binary(self, e: ast.Binary) -> str:
        lt, rt = self._expr(e.left), self._expr(e.right)
        if lt == ERR or rt == ERR:
            return ERR
        op = e.op
        if op in ("+", "-", "*", "/"):
            if lt in NUMERIC and rt in NUMERIC:
                if op == "/" and self._is_zero_literal(e.right):
                    self._err(e, "Division by zero")
                    return ERR
                return "float" if "float" in (lt, rt) else "int"
            self._err(e, f"Operator '{op}' needs numeric operands, found {lt} and {rt}")
            return ERR
        if op == "%":
            if lt == "int" and rt == "int":
                if self._is_zero_literal(e.right):
                    self._err(e, "Modulo by zero")
                    return ERR
                return "int"
            self._err(e, f"Operator '%' needs int operands, found {lt} and {rt}")
            return ERR
        if op in ("<", ">", "<=", ">="):
            if lt in NUMERIC and rt in NUMERIC:
                return "bool"
            self._err(e, f"Operator '{op}' needs numeric operands, found {lt} and {rt}")
            return ERR
        if op in ("==", "!="):
            if (lt in NUMERIC and rt in NUMERIC) or (lt == "bool" and rt == "bool"):
                return "bool"
            self._err(e, f"Cannot compare {lt} with {rt} using '{op}'")
            return ERR
        if op in ("&&", "||"):
            if lt == "bool" and rt == "bool":
                return "bool"
            self._err(e, f"Operator '{op}' needs bool operands, found {lt} and {rt}")
            return ERR
        self._err(e, f"Unknown operator '{op}'")
        return ERR

    @staticmethod
    def _is_zero_literal(e: ast.Expr) -> bool:
        return isinstance(e, ast.Literal) and e.literal_type in NUMERIC and e.value == 0


def analyze(program: ast.Program) -> SemanticResult:
    """Run semantic analysis and return all collected errors."""
    return SemanticAnalyzer().analyze(program)


def check(program: ast.Program) -> SemanticResult:
    """Like :func:`analyze` but raises :class:`SemanticErrors` on failure."""
    result = analyze(program)
    if not result.ok:
        raise SemanticErrors(result.errors)
    return result
