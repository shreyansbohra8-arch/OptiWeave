"""Constant Folding (CF): evaluate constant expressions at compile time.

* ``t = 10 + 20``  ->  ``t = 30``
* ``t = -5``       ->  ``t = -5`` (folded unary)
* ``if true goto A else B`` -> ``goto A`` (branch folding)

Division / modulo by zero is *not* folded (it is a run-time error that must be
preserved) and results that are not finite floats are left unfolded.
"""
from __future__ import annotations

from compiler.ir import (Assign, BinOp, CondJump, Const, IRProgram, Jump, UnOp, coerce,
                         evaluate_binop, evaluate_unop, is_finite)
from utils.exceptions import ExecutionError

NAME = "CF"


def run(ir: IRProgram) -> tuple[IRProgram, int]:
    out, changes = [], 0
    for ins in ir.instructions:
        new = ins
        if isinstance(ins, BinOp) and isinstance(ins.left, Const) and isinstance(ins.right, Const):
            try:
                value = evaluate_binop(ins.op, ins.left.value, ins.right.value)
            except ExecutionError:
                value = None
            if value is not None and is_finite(value):
                new = Assign(ins.dst, Const(coerce(value, ir.var_types.get(ins.dst))))
        elif isinstance(ins, UnOp) and isinstance(ins.src, Const):
            value = evaluate_unop(ins.op, ins.src.value)
            if is_finite(value):
                new = Assign(ins.dst, Const(coerce(value, ir.var_types.get(ins.dst))))
        elif isinstance(ins, CondJump) and isinstance(ins.cond, Const):
            new = Jump(ins.true_target if ins.cond.value else ins.false_target)
        if new is not ins:
            changes += 1
        out.append(new)
    return ir.with_instructions(out), changes
