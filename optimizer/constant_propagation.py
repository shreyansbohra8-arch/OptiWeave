"""Constant Propagation (CP): global forward data-flow analysis over the CFG.

State per program point: a map ``variable -> constant`` (absent = not known constant).
Meet at a join point is intersection of the predecessor states that agree on both
the value and its type, so conflicting values are never propagated. Loops are handled
by iterating to a fixed point from an optimistic initial state.
"""
from __future__ import annotations

from compiler.cfg import CFG
from compiler.ir import (Assign, BinOp, Const, IRProgram, UnOp, Var, coerce, defs,
                         evaluate_binop, evaluate_unop, is_finite)
from optimizer._common import map_operands
from utils.exceptions import ExecutionError

NAME = "CP"
_UNKNOWN = object()


def _val(op, state):
    return op.value if isinstance(op, Const) else state.get(op.name, _UNKNOWN)


def _eval(ins, state):
    if isinstance(ins, Assign):
        return _val(ins.src, state)
    if isinstance(ins, BinOp):
        a, b = _val(ins.left, state), _val(ins.right, state)
        if a is _UNKNOWN or b is _UNKNOWN:
            return _UNKNOWN
        try:
            v = evaluate_binop(ins.op, a, b)
        except ExecutionError:
            return _UNKNOWN
        return v if is_finite(v) else _UNKNOWN
    if isinstance(ins, UnOp):
        a = _val(ins.src, state)
        if a is _UNKNOWN:
            return _UNKNOWN
        v = evaluate_unop(ins.op, a)
        return v if is_finite(v) else _UNKNOWN
    return _UNKNOWN


def _transfer(ins, state: dict, types: dict) -> None:
    d = defs(ins)
    if d is None:
        return
    v = _eval(ins, state)
    if v is _UNKNOWN:
        state.pop(d, None)
    else:
        state[d] = coerce(v, types.get(d))


def _same(a: dict, b: dict) -> bool:
    return a.keys() == b.keys() and all(type(a[k]) is type(b[k]) and a[k] == b[k] for k in a)


def _meet(states: list[dict]) -> dict:
    first, rest = states[0], states[1:]
    return {k: v for k, v in first.items()
            if all(k in s and type(s[k]) is type(v) and s[k] == v for s in rest)}


def run(ir: IRProgram) -> tuple[IRProgram, int]:
    cfg = CFG.build(ir)
    if not cfg.blocks:
        return ir, 0
    types = ir.var_types
    out_state: dict[int, dict | None] = {b.id: None for b in cfg.blocks}
    in_state: dict[int, dict | None] = {b.id: None for b in cfg.blocks}

    def compute_in(b) -> dict | None:
        if b.id == cfg.entry:
            return {}
        outs = [out_state[p] for p in cfg.predecessors[b.id] if out_state[p] is not None]
        return _meet(outs) if outs else None

    for _ in range(100 * (len(cfg.blocks) + 1)):
        changed = False
        for b in cfg.blocks:
            st = compute_in(b)
            if st is None:
                continue
            in_state[b.id] = dict(st)
            cur = dict(st)
            for ins in b.instructions:
                _transfer(ins, cur, types)
            if out_state[b.id] is None or not _same(out_state[b.id], cur):
                out_state[b.id] = cur
                changed = True
        if not changed:
            break

    new_instrs, changes = [], 0
    for b in cfg.blocks:
        st = in_state[b.id]
        if st is None:  # unreachable block: leave untouched
            new_instrs.extend(b.instructions)
            continue
        st = dict(st)
        for ins in b.instructions:
            def sub(op, st=st):
                nonlocal changes
                if isinstance(op, Var) and op.name in st:
                    changes += 1
                    return Const(st[op.name])
                return op
            new = map_operands(ins, sub)
            new_instrs.append(new)
            _transfer(new, st, types)
    return ir.with_instructions(new_instrs), changes
