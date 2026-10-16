"""AST -> three-address code."""
from __future__ import annotations

from compiler import ast_nodes as ast
from compiler.ir import (Assign, BinOp, CondJump, Const, IRProgram, Jump, Label, Operand,
                         Print, UnOp, Var)

DEFAULTS = {"int": 0, "float": 0.0, "bool": False}


class IRGenerator:
    """Walks a type-annotated AST and emits an :class:`IRProgram`."""

    def __init__(self, user_names: set[str] | None = None) -> None:
        self.ir = IRProgram()
        self._temp_n = 0
        self._label_n = 0
        self._reserved = set(user_names or ())

    # -- name generation -------------------------------------------------------------
    def _temp(self, type_: str) -> str:
        while True:
            self._temp_n += 1
            name = f"t{self._temp_n}"
            if name not in self._reserved:
                break
        self.ir.temps.add(name)
        self.ir.var_types[name] = type_
        return name

    def _label(self) -> str:
        self._label_n += 1
        return f"L{self._label_n}"

    def _emit(self, ins) -> None:
        self.ir.instructions.append(ins)

    # -- entry --------------------------------------------------------------------------
    def generate(self, program: ast.Program) -> IRProgram:
        for s in program.statements:
            self._stmt(s)
        return self.ir

    # -- statements -----------------------------------------------------------------------
    def _stmt(self, s: ast.Stmt) -> None:
        if isinstance(s, ast.VarDecl):
            self.ir.var_types[s.name] = s.var_type
            src = self._expr(s.init) if s.init is not None else Const(DEFAULTS[s.var_type])
            self._emit(Assign(s.name, self._widen(src, s.var_type)))
        elif isinstance(s, ast.Assign):
            src = self._expr(s.value)
            self._emit(Assign(s.name, self._widen(src, self.ir.var_types[s.name])))
        elif isinstance(s, ast.Print):
            self._emit(Print(self._expr(s.value)))
        elif isinstance(s, ast.Block):
            for inner in s.statements:
                self._stmt(inner)
        elif isinstance(s, ast.If):
            self._if(s)
        elif isinstance(s, ast.While):
            self._while(s)

    @staticmethod
    def _widen(src: Operand, target: str) -> Operand:
        """Convert int constants assigned to float variables at IR-generation time."""
        if target == "float" and isinstance(src, Const) and type(src.value) is int:
            return Const(float(src.value))
        return src

    def _if(self, s: ast.If) -> None:
        cond = self._expr(s.condition)
        l_then, l_end = self._label(), self._label()
        if s.else_block is None:
            self._emit(CondJump(cond, l_then, l_end))
            self._emit(Label(l_then))
            self._stmt(s.then_block)
            self._emit(Label(l_end))
        else:
            l_else = self._label()
            self._emit(CondJump(cond, l_then, l_else))
            self._emit(Label(l_then))
            self._stmt(s.then_block)
            self._emit(Jump(l_end))
            self._emit(Label(l_else))
            self._stmt(s.else_block)
            self._emit(Label(l_end))

    def _while(self, s: ast.While) -> None:
        l_cond, l_body, l_end = self._label(), self._label(), self._label()
        self._emit(Label(l_cond))
        cond = self._expr(s.condition)
        self._emit(CondJump(cond, l_body, l_end))
        self._emit(Label(l_body))
        self._stmt(s.body)
        self._emit(Jump(l_cond))
        self._emit(Label(l_end))

    # -- expressions ------------------------------------------------------------------------
    def _expr(self, e: ast.Expr) -> Operand:
        if isinstance(e, ast.Literal):
            return Const(e.value)
        if isinstance(e, ast.Variable):
            return Var(e.name)
        if isinstance(e, ast.Unary):
            src = self._expr(e.operand)
            t = self._temp(e.type or "int")
            self._emit(UnOp(t, e.op, src))
            return Var(t)
        if isinstance(e, ast.Binary):
            if e.op in ("&&", "||"):
                return self._short_circuit(e)
            left = self._expr(e.left)
            right = self._expr(e.right)
            t = self._temp(e.type or "int")
            self._emit(BinOp(t, e.op, left, right))
            return Var(t)
        raise TypeError(f"Cannot generate IR for {type(e).__name__}")

    def _short_circuit(self, e: ast.Binary) -> Operand:
        res = self._temp("bool")
        l_rhs, l_end = self._label(), self._label()
        left = self._expr(e.left)
        self._emit(Assign(res, left))
        if e.op == "&&":
            self._emit(CondJump(Var(res), l_rhs, l_end))
        else:
            self._emit(CondJump(Var(res), l_end, l_rhs))
        self._emit(Label(l_rhs))
        right = self._expr(e.right)
        self._emit(Assign(res, right))
        self._emit(Label(l_end))
        return Var(res)


def generate_ir(program: ast.Program, user_names: set[str] | None = None) -> IRProgram:
    return IRGenerator(user_names).generate(program)
