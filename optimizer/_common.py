"""Helpers shared by optimisation passes."""
from __future__ import annotations

from typing import Callable

from compiler.ir import Assign, BinOp, CondJump, Const, Instruction, Operand, Print, UnOp, Var


def map_operands(ins: Instruction, fn: Callable[[Operand], Operand]) -> Instruction:
    """Return ``ins`` with every *used* operand passed through ``fn`` (defs untouched)."""
    if isinstance(ins, Assign):
        return Assign(ins.dst, fn(ins.src))
    if isinstance(ins, BinOp):
        return BinOp(ins.dst, ins.op, fn(ins.left), fn(ins.right))
    if isinstance(ins, UnOp):
        return UnOp(ins.dst, ins.op, fn(ins.src))
    if isinstance(ins, CondJump):
        return CondJump(fn(ins.cond), ins.true_target, ins.false_target)
    if isinstance(ins, Print):
        return Print(fn(ins.src))
    return ins
