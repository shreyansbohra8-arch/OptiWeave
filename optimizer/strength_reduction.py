"""Strength Reduction and Algebraic Simplification (SR).

Replaces expensive or redundant arithmetic with cheaper equivalents:

  x * 2     → x + x         (multiply to add)
  x + 0     → x             (additive identity)
  0 + x     → x             (additive identity, commutative)
  x - 0     → x             (subtractive identity)
  x * 1     → x             (multiplicative identity)
  1 * x     → x             (multiplicative identity, commutative)
  x * 0     → 0             (multiplicative annihilation)
  0 * x     → 0             (multiplicative annihilation, commutative)
  x / 1     → x             (division identity)
  x - x     → 0             (self-cancellation, same variable only)

All rewrites preserve OptiWeave's type semantics (int / float / bool).
"""
from __future__ import annotations

from compiler.ir import Assign, BinOp, Const, IRProgram, Var

NAME = "SR"


def _zero_for(dst: str, types: dict) -> Const:
    """Return a typed zero (``0`` or ``0.0``) matching the destination type."""
    return Const(0.0 if types.get(dst) == "float" else 0)


def _try_reduce(ins: BinOp, types: dict):
    """Return a simplified instruction or the original if no rule applies."""
    l, r, op, dst = ins.left, ins.right, ins.op, ins.dst
    l_const = isinstance(l, Const)
    r_const = isinstance(r, Const)

    # -- additive identity: x + 0 → x, 0 + x → x --------------------------
    if op == "+":
        if r_const and r.value == 0:
            return Assign(dst, l)
        if l_const and l.value == 0:
            return Assign(dst, r)

    # -- subtractive identity: x - 0 → x -----------------------------------
    if op == "-":
        if r_const and r.value == 0:
            return Assign(dst, l)
        # self-cancellation: x - x → 0 (only same variable)
        if isinstance(l, Var) and isinstance(r, Var) and l.name == r.name:
            return Assign(dst, _zero_for(dst, types))

    # -- multiplicative identities and annihilation -------------------------
    if op == "*":
        if (r_const and r.value == 0) or (l_const and l.value == 0):
            return Assign(dst, _zero_for(dst, types))
        if r_const and r.value == 1:
            return Assign(dst, l)
        if l_const and l.value == 1:
            return Assign(dst, r)
        # strength reduction: x * 2 → x + x
        if r_const and r.value == 2 and isinstance(l, Var):
            return BinOp(dst, "+", l, l)
        if l_const and l.value == 2 and isinstance(r, Var):
            return BinOp(dst, "+", r, r)

    # -- division identity: x / 1 → x --------------------------------------
    if op == "/":
        if r_const and r.value == 1:
            return Assign(dst, l)

    return ins


def run(ir: IRProgram) -> tuple[IRProgram, int]:
    out: list = []
    changes = 0
    for ins in ir.instructions:
        if isinstance(ins, BinOp):
            new = _try_reduce(ins, ir.var_types)
            if new is not ins:
                changes += 1
            out.append(new)
        else:
            out.append(ins)
    return ir.with_instructions(out), changes
