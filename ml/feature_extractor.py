"""Extraction of numeric features from the *original* IR and CFG.

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
11. constant_expression_ratio  constant_expression_count / instruction_count
12. duplicate_expression_ratio duplicate_expression_count / instruction_count
13. assignment_ratio           assignment_count / instruction_count
14. branch_ratio               branch_count / instruction_count
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
    "constant_expression_ratio",
    "duplicate_expression_ratio",
    "assignment_ratio",
    "branch_ratio",
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


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return numerator / denominator, or 0.0 when denominator is zero."""
    return round(numerator / denominator, 6) if denominator > 0 else 0.0


def extract_features(ir: IRProgram, cfg: CFG | None = None) -> dict[str, float]:
    """Return the features as an ordered ``{name: value}`` dict."""
    cfg = cfg or CFG.build(ir)
    real = [i for i in ir.instructions if not isinstance(i, Label)]
    names = set()
    for ins in real:
        d = defs(ins)
        if d is not None:
            names.add(d)
        names.update(o.name for o in operands(ins) if not isinstance(o, Const))

    ic = len(real)
    const_expr = sum(
        1 for i in real
        if isinstance(i, (BinOp, UnOp)) and all(isinstance(o, Const) for o in operands(i)))
    dup_expr = _duplicate_expressions(cfg)
    assign_ct = sum(1 for i in real if isinstance(i, Assign))
    branch_ct = sum(1 for i in real if isinstance(i, CondJump))

    values = {
        "instruction_count": ic,
        "arithmetic_op_count": sum(1 for i in real if isinstance(i, BinOp) and i.op in ARITH_OPS),
        "branch_count": branch_ct,
        "loop_count": len(cfg.back_edges()),
        "basic_block_count": len(cfg.blocks),
        "constant_expression_count": const_expr,
        "duplicate_expression_count": dup_expr,
        "assignment_count": assign_ct,
        "distinct_variable_count": len([n for n in names if n not in ir.temps]),
        "cfg_edge_count": cfg.edge_count,
        "constant_expression_ratio": _safe_ratio(const_expr, ic),
        "duplicate_expression_ratio": _safe_ratio(dup_expr, ic),
        "assignment_ratio": _safe_ratio(assign_ct, ic),
        "branch_ratio": _safe_ratio(branch_ct, ic),
    }
    return {name: values[name] for name in FEATURE_NAMES}


def feature_vector(features: dict[str, float]) -> list[float]:
    return [features[name] for name in FEATURE_NAMES]
