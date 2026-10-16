"""Three-address-code IR: operands, instructions, program container, evaluation helpers."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Union

from utils.exceptions import ExecutionError

ARITH_OPS = ("+", "-", "*", "/", "%")
REL_OPS = ("<", ">", "<=", ">=", "==", "!=")
COMMUTATIVE_OPS = ("+", "*", "==", "!=")
INT_MIN, INT_MAX = -(2**63), 2**63 - 1


# -- operands ---------------------------------------------------------------------
@dataclass(frozen=True)
class Var:
    name: str

    def __str__(self) -> str:
        return self.name


class Const:
    """Typed constant. Equality distinguishes ``1``, ``1.0`` and ``True``."""

    __slots__ = ("value",)

    def __init__(self, value: Union[int, float, bool]) -> None:
        object.__setattr__(self, "value", value)

    def __setattr__(self, *_):  # immutable
        raise AttributeError("Const is immutable")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Const) and type(other.value) is type(self.value) \
            and other.value == self.value

    def __hash__(self) -> int:
        return hash((type(self.value).__name__, self.value))

    def __repr__(self) -> str:
        return f"Const({self.value!r})"

    def __str__(self) -> str:
        return format_value(self.value)


Operand = Union[Var, Const]


def format_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    return str(v)


def value_type(v: object) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, float):
        return "float"
    return "int"


# -- instructions -----------------------------------------------------------------
@dataclass(frozen=True)
class Assign:
    dst: str
    src: Operand

    def __str__(self) -> str:
        return f"{self.dst} = {self.src}"


@dataclass(frozen=True)
class BinOp:
    dst: str
    op: str
    left: Operand
    right: Operand

    def __str__(self) -> str:
        return f"{self.dst} = {self.left} {self.op} {self.right}"


@dataclass(frozen=True)
class UnOp:
    dst: str
    op: str
    src: Operand

    def __str__(self) -> str:
        return f"{self.dst} = {self.op}{self.src}"


@dataclass(frozen=True)
class Label:
    name: str

    def __str__(self) -> str:
        return f"{self.name}:"


@dataclass(frozen=True)
class Jump:
    target: str

    def __str__(self) -> str:
        return f"goto {self.target}"


@dataclass(frozen=True)
class CondJump:
    cond: Operand
    true_target: str
    false_target: str

    def __str__(self) -> str:
        return f"if {self.cond} goto {self.true_target} else {self.false_target}"


@dataclass(frozen=True)
class Print:
    src: Operand

    def __str__(self) -> str:
        return f"print {self.src}"


Instruction = Union[Assign, BinOp, UnOp, Label, Jump, CondJump, Print]


def defs(ins: Instruction) -> Optional[str]:
    """Name defined by ``ins`` (or ``None``)."""
    if isinstance(ins, (Assign, BinOp, UnOp)):
        return ins.dst
    return None


def operands(ins: Instruction) -> list[Operand]:
    if isinstance(ins, Assign):
        return [ins.src]
    if isinstance(ins, BinOp):
        return [ins.left, ins.right]
    if isinstance(ins, UnOp):
        return [ins.src]
    if isinstance(ins, CondJump):
        return [ins.cond]
    if isinstance(ins, Print):
        return [ins.src]
    return []


def uses(ins: Instruction) -> list[str]:
    return [o.name for o in operands(ins) if isinstance(o, Var)]


def is_terminator(ins: Instruction) -> bool:
    return isinstance(ins, (Jump, CondJump))


def expr_key(ins: BinOp) -> tuple:
    """Canonical key of a binary expression (operands sorted for commutative ops)."""
    l, r = ins.left, ins.right
    if ins.op in COMMUTATIVE_OPS and repr(l) > repr(r):
        l, r = r, l
    return (ins.op, l, r)


# -- program container --------------------------------------------------------------
@dataclass
class IRProgram:
    instructions: list = field(default_factory=list)
    var_types: dict = field(default_factory=dict)
    temps: set = field(default_factory=set)

    def copy(self) -> "IRProgram":
        return IRProgram(list(self.instructions), dict(self.var_types), set(self.temps))

    def with_instructions(self, instrs: list) -> "IRProgram":
        return IRProgram(list(instrs), dict(self.var_types), set(self.temps))

    @property
    def instruction_count(self) -> int:
        """Number of real instructions (labels are markers and are not counted)."""
        return sum(1 for i in self.instructions if not isinstance(i, Label))

    def to_text(self, numbered: bool = False) -> str:
        lines = []
        n = 0
        for ins in self.instructions:
            if isinstance(ins, Label):
                lines.append(str(ins))
            else:
                n += 1
                prefix = f"{n:3d}:  " if numbered else "    "
                lines.append(f"{prefix}{ins}")
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, IRProgram) and self.instructions == other.instructions


# -- shared evaluation semantics (used by constant folding and the interpreter) ---------
def wrap_int(v: int) -> int:
    """Wrap to signed 64-bit like C ``long long`` with -fwrapv."""
    return (v + 2**63) % 2**64 - 2**63


def _trunc_div(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def evaluate_binop(op: str, a: object, b: object) -> object:
    """Evaluate a binary operator with OptiWeave semantics.

    Raises :class:`ExecutionError` on division/modulo by zero.
    """
    both_int = value_type(a) == "int" and value_type(b) == "int"
    if op == "+":
        return wrap_int(a + b) if both_int else float(a) + float(b)
    if op == "-":
        return wrap_int(a - b) if both_int else float(a) - float(b)
    if op == "*":
        return wrap_int(a * b) if both_int else float(a) * float(b)
    if op == "/":
        if b == 0:
            raise ExecutionError("division by zero")
        return wrap_int(_trunc_div(a, b)) if both_int else float(a) / float(b)
    if op == "%":
        if b == 0:
            raise ExecutionError("modulo by zero")
        return wrap_int(a - _trunc_div(a, b) * b)
    if op == "<":
        return a < b
    if op == ">":
        return a > b
    if op == "<=":
        return a <= b
    if op == ">=":
        return a >= b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    raise ExecutionError(f"unknown binary operator {op!r}")


def evaluate_unop(op: str, a: object) -> object:
    if op == "-":
        return wrap_int(-a) if value_type(a) == "int" else -a
    if op == "!":
        return not a
    raise ExecutionError(f"unknown unary operator {op!r}")


def coerce(value: object, type_name: Optional[str]) -> object:
    """Convert ``value`` to the declared type of the destination (int->float only)."""
    if type_name == "float" and value_type(value) == "int":
        return float(value)
    return value


def is_finite(value: object) -> bool:
    return not (isinstance(value, float) and (math.isinf(value) or math.isnan(value)))


def can_fault(ins: Instruction) -> bool:
    """True if executing ``ins`` may raise a run-time error (division/modulo)."""
    if isinstance(ins, BinOp) and ins.op in ("/", "%"):
        return not (isinstance(ins.right, Const) and ins.right.value != 0)
    return False
