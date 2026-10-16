"""Extraction of exactly ten numeric features from the *original* IR and CFG.

Feature definitions (computed before any optimisation, so no label leakage):
 1. instruction_count        non-label IR instructions
 2. arithmetic_op_count      binary + - * / % instructions
 3. branch_count             conditional jumps
 4. loop_count               CFG back edges (edge whose head dominates its tail)
 5. basic_block_count        number of basic blocks
 6. constant_expression_count  BinOp/UnOp instructions whose operands are all constants
 7. duplicate_expression_count BinOp instructions repeating an expression that is already
                             available earlier in the same basic block (operands not
                             redefined in between; commutative operands normalised)
 8. assignment_count         plain copy/assignment instructions (dst = src)
 9. distinct_variable_count  distinct user (non-temporary) variables referenced
10. cfg_edge_count           edges in the control-flow graph
"""
from __future__ import annotations

from compiler.cfg import CFG
from compiler.ir import (ARITH_OPS, Assign, BinOp, CondJump, Const, IRProgram, Label, UnOp,
                         defs, expr_key, operands)

FEATURE_NAMES: list[str] = [
    "instruction_count",
    "arithmetic_op_count",
    "branch_count",
    "loop_count",
    "basic_block_count",
    "constant_expression_count",
    "duplicate_expression_count",
    "assignment_count",
    "distinct_variable_count",
    "cfg_edge_count",
]


def _duplicate_expressions(cfg: CFG) -> int:
    dups = 0
    for block in cfg.blocks:
        seen: set[tuple] = set()
        for ins in block.instructions:
            if isinstance(ins, BinOp):
                key = expr_key(ins)
                if key in seen:
                    dups += 1
                else:
                    seen.add(key)
            d = defs(ins)
            if d is not None:
                seen = {k for k in seen
                        if not any(getattr(o, "name", None) == d for o in k[1:])}
                # a self-referential expression (x = x + 1) is not available after the def
    return dups


def extract_features(ir: IRProgram, cfg: CFG | None = None) -> dict[str, int]:
    """Return the ten features as an ordered ``{name: value}`` dict."""
    cfg = cfg or CFG.build(ir)
    real = [i for i in ir.instructions if not isinstance(i, Label)]
    names = set()
    for ins in real:
        d = defs(ins)
        if d is not None:
            names.add(d)
        names.update(o.name for o in operands(ins) if not isinstance(o, Const))
    values = {
        "instruction_count": len(real),
        "arithmetic_op_count": sum(1 for i in real if isinstance(i, BinOp) and i.op in ARITH_OPS),
        "branch_count": sum(1 for i in real if isinstance(i, CondJump)),
        "loop_count": len(cfg.back_edges()),
        "basic_block_count": len(cfg.blocks),
        "constant_expression_count": sum(
            1 for i in real
            if isinstance(i, (BinOp, UnOp)) and all(isinstance(o, Const) for o in operands(i))),
        "duplicate_expression_count": _duplicate_expressions(cfg),
        "assignment_count": sum(1 for i in real if isinstance(i, Assign)),
        "distinct_variable_count": len([n for n in names if n not in ir.temps]),
        "cfg_edge_count": cfg.edge_count,
    }
    return {name: int(values[name]) for name in FEATURE_NAMES}


def feature_vector(features: dict[str, int]) -> list[int]:
    return [features[name] for name in FEATURE_NAMES]
