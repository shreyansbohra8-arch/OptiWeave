"""Copy Propagation (COP): local forward propagation of variable-to-variable copies.

When ``x = y`` is a simple copy and neither variable is subsequently redefined,
later uses of ``x`` in the same basic block are replaced with ``y``.  This creates
opportunities for Dead Code Elimination to remove the original copy assignment.

Scope is deliberately local (one basic block) to keep the analysis simple and safe.
"""
from __future__ import annotations

from compiler.cfg import CFG
from compiler.ir import Assign, IRProgram, Var, defs
from optimizer._common import map_operands

NAME = "COP"


def run(ir: IRProgram) -> tuple[IRProgram, int]:
    cfg = CFG.build(ir)
    out: list = []
    changes = 0
    for b in cfg.blocks:
        # copies maps dst_name -> src_name for active variable-to-variable copies
        copies: dict[str, str] = {}
        for ins in b.instructions:
            # Apply active copy substitutions to operand uses
            if copies:
                def _sub(op, _copies=dict(copies)):
                    nonlocal changes
                    if isinstance(op, Var) and op.name in _copies:
                        changes += 1
                        return Var(_copies[op.name])
                    return op
                ins = map_operands(ins, _sub)

            # Update the copy map based on definitions
            d = defs(ins)
            if d is not None:
                # Invalidate any copy whose source or destination is being redefined
                copies = {k: v for k, v in copies.items() if v != d and k != d}
                # Record a new copy if this is ``dst = Var(src)``
                if isinstance(ins, Assign) and isinstance(ins.src, Var):
                    copies[d] = ins.src.name

            out.append(ins)
    return ir.with_instructions(out), changes
